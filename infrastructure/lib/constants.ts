export const Constants = {

    /******************************************************************************************
     * Table Name
    ******************************************************************************************/
    CACHE_TABLE: "ai-demo-cache",
    SESSIONS_TABLE: "ai-demo-sessions",

    /******************************************************************************************
     * Buckets Name
    ******************************************************************************************/
    VIDEO_UPLOAD_BUCKET: `ai-demo-uploads-${process.env.CDK_DEFAULT_ACCOUNT}`,
    VIDEO_PROCESSING_BUCKET: `ai-demo-processing-${process.env.CDK_DEFAULT_ACCOUNT}`,
    FINAL_VIDEO_BUCKET: `ai-demo-output-${process.env.CDK_DEFAULT_ACCOUNT}`,
    
    /******************************************************************************************
     * Lambdas Name
    ******************************************************************************************/
    ANALYSIS_LAMBDA: 'ai-demo-analysis',
    SESSION_LAMBDA: 'ai-demo-session',
    VIDEO_LAMBDA: 'ai-demo-video',
    NOTIFICATION_LAMBDA: 'ai-demo-notification',

    /******************************************************************************************
     * State Machine Name
    ******************************************************************************************/
    ANALYSIS_PIPELINE: 'ai-demo-analysis-pipeline',
    VIDEO_PIPELINE: 'ai-demo-video-pipeline',

    /******************************************************************************************
     * Rest API Name
    ******************************************************************************************/
    REST_API_NAME: 'ai-demo-api',
    REST_API_DESC: 'API for AI Demo Builder',

    /******************************************************************************************
     * Log Group Name
    ******************************************************************************************/
    LOG_GROUP_NAME: '/aws/stepfunctions/ai-demo-analysis-pipeline'



}