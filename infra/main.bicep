// NOCLAR Initial Assessment Agent — AI Foundry Workshop
//
// Resource-group-scoped deployment. The participant (or instructor) creates
// the resource group ahead of `azd provision`; this template deploys the
// workshop services into that RG. Use `scripts/provision-rg.{ps1,sh}` to
// drive provisioning at scale across participant RGs.

targetScope = 'resourceGroup'

@minLength(1)
@maxLength(64)
@description('azd environment name')
param environmentName string

@minLength(1)
@description('Azure region (use swedencentral where we have quota)')
param location string = resourceGroup().location

@description('Principal ID of the deploying user (azd populates from `azd auth login`)')
param principalId string = ''

@description('TPM capacity (thousands) for the default gpt-4.1-mini deployment. Keep modest.')
param defaultModelCapacity int = 50

@description('Default chat model name to deploy')
param defaultModelName string = 'gpt-4.1-mini'

@description('Default chat model version')
param defaultModelVersion string = '2025-04-16'

@description('Embedding model name (used by Lab 03 hybrid retrieval)')
param embeddingModelName string = 'text-embedding-3-small'

@description('Embedding model version')
param embeddingModelVersion string = '1'

@description('TPM capacity (thousands) for the embedding model deployment.')
param embeddingModelCapacity int = 30

@description('Deploy the realtime speech-to-speech model for the optional Lab 04 Voice Live demo. Leave false unless the subscription has realtime model quota.')
param deployRealtimeModel bool = false

@description('Realtime speech-to-speech model for the Lab 04 Voice Live demo')
param realtimeModelName string = 'gpt-realtime-1.5'

@description('Realtime model version')
param realtimeModelVersion string = '2026-02-23'

@description('TPM capacity (thousands) for the realtime model. One concurrent session is enough.')
param realtimeModelCapacity int = 10

var resourceToken = toLower(uniqueString(resourceGroup().id, environmentName, location))

var tags = {
  'azd-env-name': environmentName
  workshop: 'foundry-workshop'
  date: '2026-05-21'
  'environment-type': 'workshop'
}

module monitoring 'modules/monitoring.bicep' = {
  name: 'monitoring'
  params: {
    resourceToken: resourceToken
    location: location
    tags: tags
  }
}

module storage 'modules/storage.bicep' = {
  name: 'storage'
  params: {
    resourceToken: resourceToken
    location: location
    tags: tags
  }
}

module search 'modules/search.bicep' = {
  name: 'search'
  params: {
    resourceToken: resourceToken
    location: location
    tags: tags
  }
}

module foundry 'modules/foundry.bicep' = {
  name: 'foundry'
  params: {
    resourceToken: resourceToken
    location: location
    tags: tags
    defaultModelName: defaultModelName
    defaultModelVersion: defaultModelVersion
    defaultModelCapacity: defaultModelCapacity
    embeddingModelName: embeddingModelName
    embeddingModelVersion: embeddingModelVersion
    embeddingModelCapacity: embeddingModelCapacity
    deployRealtimeModel: deployRealtimeModel
    realtimeModelName: realtimeModelName
    realtimeModelVersion: realtimeModelVersion
    realtimeModelCapacity: realtimeModelCapacity
    appInsightsId: monitoring.outputs.appInsightsId
    appInsightsConnectionString: monitoring.outputs.appInsightsConnectionString
  }
}

module functions 'modules/functions.bicep' = {
  name: 'functions'
  params: {
    resourceToken: resourceToken
    location: location
    tags: tags
    storageName: storage.outputs.storageName
    deploymentContainerName: storage.outputs.deploymentContainerName
    appInsightsConnectionString: monitoring.outputs.appInsightsConnectionString
    foundryProjectEndpoint: foundry.outputs.projectEndpoint
    foundryModelDeployment: foundry.outputs.defaultModelDeploymentName
    searchEndpoint: search.outputs.searchEndpoint
    storageBlobEndpoint: storage.outputs.storageBlobEndpoint
    storageQueueEndpoint: storage.outputs.storageQueueEndpoint
  }
}

module rbac 'modules/rbac.bicep' = {
  name: 'rbac'
  params: {
    principalId: principalId
    functionsPrincipalId: functions.outputs.functionAppPrincipalId
    foundryPrincipalId: foundry.outputs.foundryPrincipalId
    foundryProjectPrincipalId: foundry.outputs.projectPrincipalId
    searchPrincipalId: search.outputs.searchPrincipalId
    foundryName: foundry.outputs.foundryName
    searchName: search.outputs.searchName
    storageName: storage.outputs.storageName
  }
}

// ----- Outputs (consumed by azd env get-values) -----

output AZURE_LOCATION string = location
output AZURE_RESOURCE_GROUP string = resourceGroup().name
output AZURE_TENANT_ID string = subscription().tenantId
output AZURE_SUBSCRIPTION_ID string = subscription().subscriptionId

output AZURE_AI_FOUNDRY_NAME string = foundry.outputs.foundryName
output AZURE_AI_FOUNDRY_ENDPOINT string = foundry.outputs.foundryEndpoint
output AZURE_AI_FOUNDRY_PROJECT_NAME string = foundry.outputs.projectName
output AZURE_AI_FOUNDRY_PROJECT_ENDPOINT string = foundry.outputs.projectEndpoint
output AZURE_AI_FOUNDRY_MODEL_DEPLOYMENT string = foundry.outputs.defaultModelDeploymentName
output AZURE_AI_FOUNDRY_EMBEDDING_DEPLOYMENT string = foundry.outputs.embeddingModelDeploymentName
output AZURE_AI_FOUNDRY_REALTIME_DEPLOYMENT string = foundry.outputs.realtimeModelDeploymentName
output AZURE_AI_FOUNDRY_PORTAL_URL string = 'https://ai.azure.com/build/overview?wsid=/subscriptions/${subscription().subscriptionId}/resourceGroups/${resourceGroup().name}/providers/Microsoft.CognitiveServices/accounts/${foundry.outputs.foundryName}/projects/${foundry.outputs.projectName}&tid=${subscription().tenantId}'

output AZURE_AI_SEARCH_NAME string = search.outputs.searchName
output AZURE_AI_SEARCH_ENDPOINT string = search.outputs.searchEndpoint

output AZURE_STORAGE_ACCOUNT string = storage.outputs.storageName
output AZURE_STORAGE_BLOB_ENDPOINT string = storage.outputs.storageBlobEndpoint
output AZURE_STORAGE_QUEUE_ENDPOINT string = storage.outputs.storageQueueEndpoint

output AZURE_FUNCTION_APP_NAME string = functions.outputs.functionAppName
output AZURE_FUNCTION_APP_HOSTNAME string = functions.outputs.functionAppHostname

output APPLICATIONINSIGHTS_CONNECTION_STRING string = monitoring.outputs.appInsightsConnectionString
output AZURE_LOG_ANALYTICS_WORKSPACE_NAME string = monitoring.outputs.logAnalyticsName
