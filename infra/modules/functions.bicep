// Azure Functions — Flex Consumption (Python 3.11)
// Used by: Block 4 (persist_assessment, log_request, notify_reviewer as agent tools)

@description('Resource name prefix / resourceToken')
param resourceToken string

@description('Azure region')
param location string

@description('Common tags')
param tags object

@description('Storage account name (for AzureWebJobsStorage + deployment package)')
param storageName string

@description('Deployment package container name on the storage account')
param deploymentContainerName string

@description('App Insights connection string')
param appInsightsConnectionString string

@description('Foundry project endpoint')
param foundryProjectEndpoint string

@description('Default chat model deployment name')
param foundryModelDeployment string

@description('AI Search endpoint')
param searchEndpoint string

@description('Storage blob endpoint (for function code data access)')
param storageBlobEndpoint string

@description('Storage queue endpoint (for reviewer-inbox queue trigger)')
param storageQueueEndpoint string

resource flexPlan'Microsoft.Web/serverfarms@2023-12-01' = {
  name: 'plan-${resourceToken}'
  location: location
  tags: tags
  sku: {
    name: 'FC1'
    tier: 'FlexConsumption'
  }
  properties: {
    reserved: true
  }
}

resource functionApp 'Microsoft.Web/sites@2023-12-01' = {
  name: 'func-${resourceToken}'
  location: location
  tags: union(tags, { 'azd-service-name': 'functions' })
  kind: 'functionapp,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: flexPlan.id
    httpsOnly: true
    functionAppConfig: {
      deployment: {
        storage: {
          type: 'blobContainer'
          value: '${storageBlobEndpoint}${deploymentContainerName}'
          authentication: {
            type: 'SystemAssignedIdentity'
          }
        }
      }
      scaleAndConcurrency: {
        maximumInstanceCount: 40
        instanceMemoryMB: 2048
      }
      runtime: {
        name: 'python'
        version: '3.11'
      }
    }
    siteConfig: {
      minTlsVersion: '1.2'
      ftpsState: 'Disabled'
    }
  }
}

resource appSettings 'Microsoft.Web/sites/config@2023-12-01' = {
  parent: functionApp
  name: 'appsettings'
  properties: {
    AzureWebJobsStorage__blobServiceUri: storageBlobEndpoint
    AzureWebJobsStorage__queueServiceUri: storageQueueEndpoint
    AzureWebJobsStorage__credential: 'managedidentity'
    APPLICATIONINSIGHTS_CONNECTION_STRING: appInsightsConnectionString
    AZURE_AI_FOUNDRY_PROJECT_ENDPOINT: foundryProjectEndpoint
    AZURE_AI_FOUNDRY_MODEL_DEPLOYMENT: foundryModelDeployment
    AZURE_AI_SEARCH_ENDPOINT: searchEndpoint
    AZURE_STORAGE_BLOB_ENDPOINT: storageBlobEndpoint
    AZURE_STORAGE_QUEUE_ENDPOINT: storageQueueEndpoint
    AZURE_STORAGE_ACCOUNT: storageName
    REVIEWER_QUEUE_NAME: 'reviewer-inbox'
    ASSESSMENTS_CONTAINER: 'assessments'
    LOGS_CONTAINER: 'logs'
    SAMPLE_DOCS_CONTAINER: 'sample-docs'
  }
}

output functionAppId string = functionApp.id
output functionAppName string = functionApp.name
output functionAppHostname string = functionApp.properties.defaultHostName
output functionAppPrincipalId string = functionApp.identity.principalId
