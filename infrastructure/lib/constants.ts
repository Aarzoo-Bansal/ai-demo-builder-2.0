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
    FINAL_VIDEO_BUCKET: `ai-demo-output-${process.env.CDK_DEFAULT_ACCOUNT}`
}