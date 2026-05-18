// NOCLAR Initial Assessment Agent — AI Foundry Workshop
// Composes all infra needed for Blocks 1–4. Single `azd up` provisions
// everything; per-block scripts deploy code and data on top.

targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('azd environment name')
param environmentName string

@minLength(1)
@description('Azure region (use swedencentral where we have quota)')
param location string = 'swedencentral'

@description('Principal ID of the deploying user (azd populates from `azd auth login`)')
param principalId string = ''

@description('TPM capacity (thousands) for the default o4-mini deployment. Keep modest.')
param defaultModelCapacity int = 20

@description('Default chat model name to deploy')
param defaultModelName string = 'o4-mini'

@description('Default chat model version')
param defaultModelVersion string = '2025-04-16'

var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))

var tags = {
  'azd-env-name': environmentName
  workshop: 'foundry-workshop'
  date: '2026-05-21'
  'environment-type': 'workshop'
}

resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: 'rg-${environmentName}'
  location: location
  tags: tags
}

module monitoring 'modules/monitoring.bicep' = {
  scope: rg
  name: 'monitoring'
  params: {
    resourceToken: resourceToken
    location: location
    tags: tags
  }
}

module storage 'modules/storage.bicep' = {
  scope: rg
  name: 'storage'
  params: {
    resourceToken: resourceToken
    location: location
    tags: tags
  }
}

module search 'modules/search.bicep' = {
  scope: rg
  name: 'search'
  params: {
    resourceToken: resourceToken
    location: location
    tags: tags
  }
}

module foundry 'modules/foundry.bicep' = {
  scope: rg
  name: 'foundry'
  params: {
    resourceToken: resourceToken
    location: location
    tags: tags
    defaultModelName: defaultModelName
    defaultModelVersion: defaultModelVersion
    defaultModelCapacity: defaultModelCapacity
  }
}

module functions 'modules/functions.bicep' = {
  scope: rg
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

module acs 'modules/acs.bicep' = {
  scope: rg
  name: 'acs'
  params: {
    resourceToken: resourceToken
    tags: tags
  }
}

module rbac 'modules/rbac.bicep' = {
  scope: rg
  name: 'rbac'
  params: {
    principalId: principalId
    functionsPrincipalId: functions.outputs.functionAppPrincipalId
    foundryPrincipalId: foundry.outputs.foundryPrincipalId
    foundryName: foundry.outputs.foundryName
    searchName: search.outputs.searchName
    storageName: storage.outputs.storageName
  }
}

// ----- Outputs (consumed by azd env get-values) -----

output AZURE_LOCATION string = location
output AZURE_RESOURCE_GROUP string = rg.name
output AZURE_TENANT_ID string = subscription().tenantId
output AZURE_SUBSCRIPTION_ID string = subscription().subscriptionId

output AZURE_AI_FOUNDRY_NAME string = foundry.outputs.foundryName
output AZURE_AI_FOUNDRY_ENDPOINT string = foundry.outputs.foundryEndpoint
output AZURE_AI_FOUNDRY_PROJECT_NAME string = foundry.outputs.projectName
output AZURE_AI_FOUNDRY_PROJECT_ENDPOINT string = foundry.outputs.projectEndpoint
output AZURE_AI_FOUNDRY_MODEL_DEPLOYMENT string = foundry.outputs.defaultModelDeploymentName
output AZURE_AI_FOUNDRY_PORTAL_URL string = 'https://ai.azure.com/build/overview?wsid=/subscriptions/${subscription().subscriptionId}/resourceGroups/${rg.name}/providers/Microsoft.CognitiveServices/accounts/${foundry.outputs.foundryName}/projects/${foundry.outputs.projectName}&tid=${subscription().tenantId}'

output AZURE_AI_SEARCH_NAME string = search.outputs.searchName
output AZURE_AI_SEARCH_ENDPOINT string = search.outputs.searchEndpoint

output AZURE_STORAGE_ACCOUNT string = storage.outputs.storageName
output AZURE_STORAGE_BLOB_ENDPOINT string = storage.outputs.storageBlobEndpoint
output AZURE_STORAGE_QUEUE_ENDPOINT string = storage.outputs.storageQueueEndpoint

output AZURE_FUNCTION_APP_NAME string = functions.outputs.functionAppName
output AZURE_FUNCTION_APP_HOSTNAME string = functions.outputs.functionAppHostname

output AZURE_COMMUNICATION_SERVICES_NAME string = acs.outputs.acsName
output AZURE_COMMUNICATION_SERVICES_ENDPOINT string = acs.outputs.acsEndpoint

output APPLICATIONINSIGHTS_CONNECTION_STRING string = monitoring.outputs.appInsightsConnectionString
output AZURE_LOG_ANALYTICS_WORKSPACE_NAME string = monitoring.outputs.logAnalyticsName
