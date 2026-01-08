import * as cdk from 'aws-cdk-lib'
import * as lambda from 'aws-cdk-lib/aws-lambda'
import * as sfn from 'aws-cdk-lib/aws-stepfunctions'
import * as tasks from 'aws-cdk-lib/aws-stepfunctions-tasks'
import * as logs from 'aws-cdk-lib/aws-logs'
import { Construct } from 'constructs'
import { Constants } from './constants'

interface StepFunctionsStackProps extends cdk.StackProps {
    analysisLambda: lambda.Function
    sessionLambda: lambda.Function
    videoLambda: lambda.Function
    notificationLambda: lambda.Function
}

export class StepFunctionsStack extends cdk.Stack {
    public readonly analysisPipeline: sfn.StateMachine
    public readonly videoPipeline: sfn.StateMachine

    constructor(scope: Construct, id: string, props: StepFunctionsStackProps) {
        super(scope, id, props)

        /****************************************************************************************************** 
         * Log Groups for Step Functions
        *******************************************************************************************************/
        const analysisLogGroup = new logs.LogGroup(this, 'AnalysisPipelineLogGroup', {
            logGroupName: Constants.LOG_GROUP_NAME,
            removalPolicy: cdk.RemovalPolicy.DESTROY
        })

        /****************************************************************************************************** 
         * PipeLine 1: Analysis Pipeline (Analysis -> Session)
         * Triggered by: API Gateway
         * Input: github_url
         * Input Format: { "github_url" : "https://github.com/user/repo"}
        *******************************************************************************************************/
        
        // Error handler for Analysis Lambda Exception
        const handleAnalysisException = new sfn.Pass(this, 'HandleAnalysisException', {
            parameters: {
                'statusCode': 500,
                'error': {
                    'type': 'ANALYSIS_EXCEPTION',
                    'message.$': 'States.Format(\'Analysis Lambda failed: {}\', $.Cause)'
                }
            }
        })

        const handleSessionException = new sfn.Pass(this, 'HandleSessionException', {
            parameters: {
                'statusCode': 500,
                'error': {
                    'type': 'SESSION_EXCEPTION',
                    'message.$': 'States.Format(\'Session Lambda failed: {}\', $.Cause)'
                }
            }
        })

        // Creating task to invoke Analysis Lambda
        const analysisTask = new tasks.LambdaInvoke(this, 'AnalysisTask', {
            lambdaFunction: props.analysisLambda,
            outputPath: '$.Payload',
            retryOnServiceExceptions: true
        })

        // Adding retry to the analysis lambda
        analysisTask.addRetry({
            errors: ['Lambda.ServiceException', 'Lambda.TooManyRequestsException'],
            interval: cdk.Duration.seconds(2),
            maxAttempts: 3,
            backoffRate: 2
        })

        // Adding Error Handling in case Analysis Lambda Fails
        analysisTask.addCatch(handleAnalysisException, {
            resultPath: '$'
        })

        // Creating task to invole Session Lambda
        const sessionTask = new tasks.LambdaInvoke(this, 'SessionTask', {
            lambdaFunction: props.sessionLambda,
            outputPath: '$.Payload',
            retryOnServiceExceptions: true
        })

        sessionTask.addRetry({
            errors: ['Lambda.ServiceException', 'Lambda.TooManyRequestsException'],
            interval: cdk.Duration.seconds(2),
            maxAttempts: 3,
            backoffRate: 2
        })

        sessionTask.addCatch(handleSessionException, {
            resultPath: '$'
        })

        // Check if Analysis returned a business error (statusCode >= 400)
        const checkAnalysisResult = new sfn.Choice(this, 'CheckAnalysisResult')
            .when(
                sfn.Condition.and(
                    sfn.Condition.isPresent('$.statusCode'),
                    sfn.Condition.numberGreaterThanEquals('$.statusCode', 400)
                ),
                new sfn.Pass(this, 'PassAnalysisError')
            )
            .otherwise(sessionTask)

        // Defining the chain: call session lambda after analysis lambda
        const analysisDefinition = analysisTask.next(checkAnalysisResult)

        // Cresting Analysis Pipeline State Machine
        this.analysisPipeline = new sfn.StateMachine(this, 'AiDemoAnalysisPipeline', {
            stateMachineName: Constants.ANALYSIS_PIPELINE,
            definitionBody: sfn.DefinitionBody.fromChainable(analysisDefinition),
            timeout: cdk.Duration.minutes(5),
            stateMachineType: sfn.StateMachineType.EXPRESS,
            logs: {
                destination: analysisLogGroup,
                level: sfn.LogLevel.ALL
            }
        })

        /****************************************************************************************************** 
         * PipeLine 2: Video Pipeline (Video -> Notification)
         * Triggered by: S3 event, when all the videos are uploaded
         * Input: session id
         * Input Format: { "session_id" : "abc123"}
        *******************************************************************************************************/
        const handleVideoException = new sfn.Pass(this, 'HandleVideoException', {
            parameters: {
                'statusCode': 500,
                'error': {
                    'type': 'VIDEO_EXCEPTION',
                    'message.$': 'States.Format(\'Video Lambda failed: {}\', $.Cause)'
                }
            }
        })

        const handleNotificationException = new sfn.Pass(this, 'HandleNotificationException', {
            parameters: {
                'statusCode': 500,
                'error': {
                    'type': 'NOTIFICATION_EXCEPTION',
                    'message.$': 'States.Format(\'Notification Lambda failed: {}\', $.Cause)'
                }
            }
        })

        // Creating video tasks to invoke video lambda in the step function
        const videoTask = new tasks.LambdaInvoke(this, 'VideoTask', {
            lambdaFunction: props.videoLambda,
            outputPath: '$.Payload',
            retryOnServiceExceptions: true
        })

        videoTask.addRetry({
            errors: ['Lambda.ServiceException', 'Lambda.TooManyRequestsException'],
            interval: cdk.Duration.seconds(2),
            maxAttempts: 3,
            backoffRate: 2
        })

        videoTask.addCatch(handleVideoException, {
            resultPath: '$'
        })

        // Creating notification task to invoke notification lambda in the step function
        const notificationTask = new tasks.LambdaInvoke(this, 'NotificationTask', {
            lambdaFunction: props.notificationLambda,
            outputPath: '$.Payload',
            retryOnServiceExceptions: true
        })

        notificationTask.addRetry({
            errors: ['Lambda.ServiceException', 'Lambda.TooManyRequestsException'],
            interval: cdk.Duration.seconds(2),
            maxAttempts: 3, 
            backoffRate: 2
        })

        notificationTask.addCatch(handleNotificationException, {
            resultPath: '$'
        })

        const checkVideoResult = new sfn.Choice(this, 'CheckVideoResult')
            .when(
                sfn.Condition.and(
                    sfn.Condition.isPresent('$.statusCode'),
                    sfn.Condition.numberGreaterThanEquals('$.statusCode', 400)
                ),
                new sfn.Pass(this, 'PassVideoError')
            )
            .otherwise(notificationTask)


        const videoDefinition = videoTask.next(checkVideoResult)

        this.videoPipeline = new sfn.StateMachine(this, 'VideoPipeline', {
            stateMachineName: Constants.VIDEO_PIPELINE,
            definitionBody: sfn.DefinitionBody.fromChainable(videoDefinition),
            timeout: cdk.Duration.minutes(20),
            stateMachineType: sfn.StateMachineType.STANDARD
        })
    }
}