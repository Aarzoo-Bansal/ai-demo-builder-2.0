import * as cdk from 'aws-cdk-lib'
import * as lambda from 'aws-cdk-lib/aws-lambda'
import * as sfn from 'aws-cdk-lib/aws-stepfunctions'
import * as tasks from 'aws-cdk-lib/aws-stepfunctions-tasks'
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
         * PipeLine 1: Analysis Pipeline (Analysis -> Session)
         * Triggered by: API Gateway
         * Input: github_url
         * Input Format: { "github_url" : "https://github.com/user/repo"}
        *******************************************************************************************************/

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
        analysisTask.addCatch(new sfn.Fail(this, 'AnalysisFailed', {
            cause: 'Analysis Lambda Failed',
            error: 'AnalysisError'
        }))

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

        sessionTask.addCatch(new sfn.Fail(this, 'SessionFailed', {
            cause: 'Session Lambda Failed',
            error: 'SessionError'
        }))

        // Defining the chain: call session lambda after analysis lambda
        const analysisDefinition = analysisTask.next(sessionTask)

        // Cresting Analysis Pipeline State Machine
        this.analysisPipeline = new sfn.StateMachine(this, 'AiDemoAnalysisPipeline', {
            stateMachineName: Constants.ANALYSIS_PIPELINE,
            definitionBody: sfn.DefinitionBody.fromChainable(analysisDefinition),
            timeout: cdk.Duration.minutes(5)
        })


        /****************************************************************************************************** 
         * PipeLine 2: Video Pipeline (Video -> Notification)
         * Triggered by: S3 event, when all the videos are uploaded
         * Input: session id
         * Input Format: { "session_id" : "abc123"}
        *******************************************************************************************************/
        
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

        videoTask.addCatch(new sfn.Fail(this, 'VideoFailed', {
            cause: 'Video Lambda Failed',
            error: 'VideoError'
        }))

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

        notificationTask.addCatch(new sfn.Fail(this, 'NotificationFailed', {
            cause: 'Notification Lambda Failed',
            error: 'NotificationError'
        }))

        const videoDefinition = videoTask.next(notificationTask)

        this.videoPipeline = new sfn.StateMachine(this, 'VideoPipeline', {
            stateMachineName: Constants.VIDEO_PIPELINE,
            definitionBody: sfn.DefinitionBody.fromChainable(videoDefinition),
            timeout: cdk.Duration.minutes(20)
        })
    }
}