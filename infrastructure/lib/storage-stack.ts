import * as cdk from 'aws-cdk-lib'
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb'
import * as s3 from 'aws-cdk-lib/aws-s3'
import { Construct } from 'constructs'
import { Constants } from './constants'

export class StorageStack extends cdk.Stack {
    public readonly cacheTable: dynamodb.TableV2
    public readonly sessionsTable: dynamodb.TableV2
    public readonly videoUploadsBucket: s3.Bucket
    public readonly videoProcessingBucket: s3.Bucket
    public readonly finalVideoBucket: s3.Bucket

    constructor(scope: Construct, id: string, props?: cdk.StackProps) {
        super(scope, id, props)

        /****************************************************************************************************** 
         * Creating DynamoDB Tables
        *******************************************************************************************************/
        this.cacheTable = new dynamodb.TableV2(this, 'AIDemoCache', {
            tableName: Constants.CACHE_TABLE,
            partitionKey: {
                name: "repo_url",
                type: dynamodb.AttributeType.STRING
            },
            sortKey: {
                name: 'commit_sha',
                type: dynamodb.AttributeType.STRING
            },
            timeToLiveAttribute: 'ttl',
            billing: dynamodb.Billing.onDemand(),
            removalPolicy: cdk.RemovalPolicy.DESTROY
        })

        this.sessionsTable = new dynamodb.TableV2(this, 'AIDemoSessions', {
            tableName: Constants.SESSIONS_TABLE,
            partitionKey: {
                name: "session_id",
                type: dynamodb.AttributeType.STRING
            },
            timeToLiveAttribute: 'ttl',
            billing: dynamodb.Billing.onDemand(),
            removalPolicy: cdk.RemovalPolicy.DESTROY
        })

        /****************************************************************************************************** 
         * Creating S3 Buckets
        *******************************************************************************************************/
        this.videoUploadsBucket = new s3.Bucket(this, 'AIDemoUploads', {
            bucketName: Constants.VIDEO_UPLOAD_BUCKET,
            cors: [
                {
                    allowedHeaders : ["*"],
                    allowedMethods: [s3.HttpMethods.POST, s3.HttpMethods.PUT],
                    allowedOrigins: ["*"]
                }
            ],
            lifecycleRules: [
                {
                    expiration: cdk.Duration.days(7), // Deleting the uploads after 7 days
                }
            ],
            removalPolicy: cdk.RemovalPolicy.DESTROY,
            autoDeleteObjects: true
        })

        this.videoProcessingBucket = new s3.Bucket(this, 'AiDemoProcessing', {
            bucketName: Constants.VIDEO_PROCESSING_BUCKET,
            lifecycleRules: [
                {
                    expiration: cdk.Duration.days(1) // deleting the processed videos after 1 day
                }
            ],
            removalPolicy: cdk.RemovalPolicy.DESTROY,
            autoDeleteObjects: true
        })

        this.finalVideoBucket = new s3.Bucket(this, 'AiDemoOutput', {
            bucketName: Constants.FINAL_VIDEO_BUCKET,
            cors: [
                {
                    allowedMethods: [s3.HttpMethods.GET],
                    allowedOrigins: ["*"],
                    allowedHeaders: ["*"]
                }
            ],
            lifecycleRules: [
                {
                    expiration: cdk.Duration.days(30) // Deleting demos after 30 days
                }
            ],
            removalPolicy: cdk.RemovalPolicy.DESTROY,
            autoDeleteObjects: true
        })
    }
}

