import * as cdk from 'aws-cdk-lib'
import * as apigateway from 'aws-cdk-lib/aws-apigateway'
import * as lambda from 'aws-cdk-lib/aws-lambda'
import * as sfn from 'aws-cdk-lib/aws-stepfunctions'
import * as iam from 'aws-cdk-lib/aws-iam'
import { Construct } from 'constructs'
import { Constants } from './constants'

interface ApiGatewayStackProps extends cdk.StackProps {
    analysisPipeline: sfn.StateMachine
    videoPipeline: sfn.StateMachine
    sessionLambda: lambda.Function
}

export class ApiGatewayStack extends cdk.Stack {
    public readonly api: apigateway.RestApi

    constructor(scope: Construct, id: string, props: ApiGatewayStackProps) {
        super(scope, id, props)

        /****************************************************************************************************** 
         * Create REST API
        *******************************************************************************************************/
        this.api = new apigateway.RestApi(this, 'AiDemoApi', {
            restApiName: Constants.REST_API_NAME,
            description: Constants.REST_API_DESC,
            defaultCorsPreflightOptions: {
                allowOrigins: apigateway.Cors.ALL_ORIGINS,
                allowMethods: apigateway.Cors.ALL_METHODS,
                allowHeaders: ['Content-Type', 'Authorization']
            }
        })

        /****************************************************************************************************** 
         * Post /analyze -> Triggers Analysis Pipeline (Step Function)
        *******************************************************************************************************/
        const analyzeResource = this.api.root.addResource('analyze')

        // IAM role for API Gateway to invoke step function
        const apiGatewayRole = new iam.Role(this, 'ApiGatewayStepFunctionRole', {
            assumedBy: new iam.ServicePrincipal('apigateway.amazonaws.com')
        })

        apiGatewayRole.addToPolicy(new iam.PolicyStatement({
            actions: ['states:StartSyncExecution'],
            resources: [
                props.analysisPipeline.stateMachineArn
            ]
        }))

        apiGatewayRole.addToPolicy(new iam.PolicyStatement({
            actions: ['states:StartExecution'],
            resources: [
                props.videoPipeline.stateMachineArn
            ]
        }))

        const analyzeIntegration = new apigateway.AwsIntegration({
            service: 'states',
            action: 'StartSyncExecution',
            integrationHttpMethod: 'POST',
            options: {
                credentialsRole: apiGatewayRole,
                integrationResponses: [
                    {
                        statusCode: '200',
                        responseTemplates: {
                            'application/json': `#set($body = $util.parseJson($input.body))
$body.output`
                        },
                        responseParameters: {
                            'method.response.header.Access-Control-Allow-Origin': "'*'"
                        }
                    }
                ],
                requestTemplates: {
                    'application/json': `{
                "stateMachineArn": "${props.analysisPipeline.stateMachineArn}",
                "input": "$util.escapeJavaScript($input.body)"
            }`
                }
            }
        })

        analyzeResource.addMethod('POST', analyzeIntegration, {
            methodResponses: [
                {
                    statusCode: '200',
                    responseParameters: {
                        'method.response.header.Access-Control-Allow-Origin': true
                    }
                }
            ]
        })

        /****************************************************************************************************** 
         * GET /session/{sessionId} -> Calls Session Lambda Directly
        *******************************************************************************************************/
        const sessionResource = this.api.root.addResource('session')
        const sessionIdResource = sessionResource.addResource('{sessionId}')

        // Calling the lambda function directly
        const sessionIntegration = new apigateway.LambdaIntegration(props.sessionLambda)
        sessionIdResource.addMethod('GET', sessionIntegration)

        /****************************************************************************************************** 
         * POST /session/{sessionId}/complete -> Triggers Video Pipeline (Step Function)
        *******************************************************************************************************/
        const completeResource = sessionIdResource.addResource('complete')

        const videoIntegration = new apigateway.AwsIntegration({
            service: 'states',
            action: 'StartExecution',
            options: {
                credentialsRole: apiGatewayRole,
                integrationResponses: [
                    {
                        statusCode: '200',
                        responseTemplates: {
                            'application/json': '{"status": "processing"}'
                        },
                        responseParameters: {
                            'method.response.header.Access-Control-Allow-Origin': "'*'"
                        }
                    }
                ],
                requestTemplates: {
                    'application/json': `{
        "stateMachineArn": "${props.videoPipeline.stateMachineArn}",
        "input": "{\\"session_id\\": \\"$input.params('sessionId')\\"}"
    }`
                }
            }
        })

        completeResource.addMethod('POST', videoIntegration, {
            methodResponses: [
                {
                    statusCode: '200',
                    responseParameters: {
                        'method.response.header.Access-Control-Allow-Origin': true
                    }
                }
            ]
        })

        /****************************************************************************************************** 
         * Output the API Url
        *******************************************************************************************************/
        new cdk.CfnOutput(this, 'ApiUrl', {
            value: this.api.url,
            description: 'API Gateway URL'
        })
    }
}