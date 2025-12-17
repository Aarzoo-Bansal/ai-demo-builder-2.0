#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib/core';
import { LambdaStack } from '../lib/lambdas-stack';
import { StorageStack } from '../lib/storage-stack';
import { StepFunctionsStack } from '../lib/step-functions-stack';
import { ApiGatewayStack } from '../lib/api-gateway-stack';

const app = new cdk.App();

const storage = new StorageStack(app, 'StorageStack')

const lambdas = new LambdaStack(app, 'LambdasStack', {
  cacheTable: storage.cacheTable,
  sessionTable: storage.sessionsTable,
  videoUploadsBucket: storage.videoUploadsBucket,
  videoProcessingBucket: storage.videoProcessingBucket,
  finalVideoBucket: storage.finalVideoBucket
})

const stepFunctions = new StepFunctionsStack(app, 'StepFunctionStack', {
  analysisLambda: lambdas.analysisLambda,
  sessionLambda: lambdas.sessionLambda,
  videoLambda: lambdas.videoLambda,
  notificationLambda: lambdas.notificationLambda
})

const apiGateway = new ApiGatewayStack(app, 'ApiGatewayStack', {
  analysisPipeline: stepFunctions.analysisPipeline,
  videoPipeline: stepFunctions.videoPipeline,
  sessionLambda: lambdas.sessionLambda
})

