import * as cdk from 'aws-cdk-lib'
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb'
import * as s3 from 'aws-cdk-lib/aws-s3'
import * as lambda from 'aws-cdk-lib/aws-lambda'
import { Construct } from 'constructs'
import { Constants } from './constants'
import * as iam from 'aws-cdk-lib/aws-iam'

interface LambdaStackProps extends cdk.StackProps {
    cacheTable: dynamodb.TableV2
    sessionTable: dynamodb.TableV2
    videoUploadsBucket: s3.Bucket
    videoProcessingBucket: s3.Bucket
    finalVideoBucket: s3.Bucket
}

export class LambdaStack extends cdk.Stack {
    public readonly analysisLambda: lambda.Function
    public readonly sessionLambda: lambda.Function
    public readonly videoLambda: lambda.Function
    public readonly notificationLambda: lambda.Function

    constructor(scope: Construct, id: string, props: LambdaStackProps) {
        super(scope, id, props)

        /****************************************************************************************************** 
         * Lambda 1 - Analysis Lambda
        *******************************************************************************************************/
        this.analysisLambda = new lambda.Function(this, 'AiDemoAnalysisLambda', {
            functionName: Constants.ANALYSIS_LAMBDA,
            runtime: lambda.Runtime.PYTHON_3_11,
            handler: 'handler.handler',
            code: lambda.Code.fromAsset('../services/analysis'),
            memorySize: 512,
            timeout: cdk.Duration.seconds(60),
            environment: {
                CACHE_TABLE_NAME: props.cacheTable.tableName,
            }
        })

        // Granting read and write permission to Cache Table
        props.cacheTable.grantReadWriteData(this.analysisLambda)

        /****************************************************************************************************** 
         * Lambda 2 - Sessions Lambda
        *******************************************************************************************************/
       this.sessionLambda = new lambda.Function(this, 'AiDemoSessionsLambda', {
            functionName: Constants.SESSION_LAMBDA,
            runtime: lambda.Runtime.PYTHON_3_11,
            handler: 'handler.handler',
            code: lambda.Code.fromAsset('../services/session'),
            memorySize: 512,
            timeout: cdk.Duration.seconds(60),
            environment: {
                SESSIONS_TABLE_NAME: props.sessionTable.tableName,
                UPLOADS_BUCKET: props.videoUploadsBucket.bucketName,
                OUTPUT_BUCKET: props.finalVideoBucket.bucketName
            }
       })

       // Granting the read and write permission to sessions table and uploads bucket
       props.sessionTable.grantReadWriteData(this.sessionLambda)
       props.videoUploadsBucket.grantPut(this.sessionLambda)
       props.finalVideoBucket.grantRead(this.sessionLambda)

       /****************************************************************************************************** 
         * Lambda 3 - Video Processing Lambda
       *******************************************************************************************************/
       // create an ffmpeg layer for video processing - using public layer first
       const ffmpegLayer = lambda.LayerVersion.fromLayerVersionArn(this, 'FFmpegLayer',
            'arn:aws:lambda:us-east-1:123456789:layer:ffmpeg:1'
       )


       this.videoLambda = new lambda.Function(this, 'AiDemoVideoLambda', {
            functionName: Constants.VIDEO_LAMBDA,
            runtime: lambda.Runtime.PYTHON_3_11,
            handler: 'handler.handler',
            code: lambda.Code.fromAsset('../services/video'),
            memorySize: 3072,
            timeout: cdk.Duration.minutes(15),
            environment: {
                SESSIONS_TABLE_NAME: props.sessionTable.tableName,
                UPLOADS_BUCKET: props.videoUploadsBucket.bucketName,
                PROCESSING_BUCKET: props.videoProcessingBucket.bucketName,
                OUTPUT_BUCKET: props.finalVideoBucket.bucketName
            },
            layers: [ffmpegLayer]
       })

       // Granting read and write permission to the sessions table and buckets
       props.sessionTable.grantReadWriteData(this.videoLambda)
       props.videoUploadsBucket.grantRead(this.videoLambda)
       props.videoProcessingBucket.grantReadWrite(this.videoLambda)
       props.finalVideoBucket.grantWrite(this.videoLambda)

       /****************************************************************************************************** 
         * Lambda 4 - Notification Lambda
       *******************************************************************************************************/
      this.notificationLambda = new lambda.Function(this, 'AiDemoNotificationLambda', {
            functionName: Constants.NOTIFICATION_LAMBDA,
            runtime: lambda.Runtime.PYTHON_3_11,
            handler: 'handler.handler',
            code: lambda.Code.fromAsset('../services/notification'),
            memorySize: 256,
            timeout: cdk.Duration.seconds(30),
            environment: {
                SESSIONS_TABLE_NAME: props.sessionTable.tableName,
                PROCESSING_BUCKET: props.videoProcessingBucket.bucketName
            }
      })

      props.sessionTable.grantReadData(this.notificationLambda)
      props.videoProcessingBucket.grantDelete(this.notificationLambda)

      // Granting permission to send email to the user via SES
      this.notificationLambda.addToRolePolicy(new iam.PolicyStatement({
            actions: ['ses:SendEmail', 'sesSendRawEmail'],
            resources: ['*']
      }))
    }
}