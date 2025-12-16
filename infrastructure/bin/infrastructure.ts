#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib/core';
import { LambdaStack } from '../lib/lambdas-stack';
import { StorageStack } from '../lib/storage-stack';


const app = new cdk.App();
const storage = new StorageStack(app, 'StorageStack')
const lambdas = new LambdaStack(app, 'LambdasStack', {
  cacheTable: storage.cacheTable,
  sessionTable: storage.sessionsTable,
  videoUploadsBucket: storage.videoUploadsBucket,
  videoProcessingBucket: storage.videoProcessingBucket,
  finalVideoBucket: storage.finalVideoBucket
})
