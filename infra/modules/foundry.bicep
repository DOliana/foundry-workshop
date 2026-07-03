// Azure AI Foundry account + project + gpt-5.4-mini model deployment
// Used by: every block. This is the centerpiece of the workshop.
//
// Notes:
//   * Uses the unified AIServices kind (Foundry generation, GA in 2025)
//   * TPM cap on gpt-5.4-mini is intentionally conservative so participants have
//     room to deploy additional models manually during Lab 1.

@description('Resource name prefix / resourceToken')
param resourceToken string

@description('Azure region (use swedencentral — that is where we have quota)')
param location string

@description('Common tags')
param tags object

@description('Model name for the default deployment')
param defaultModelName string = 'gpt-5.4-mini'

@description('Model version for the default deployment')
param defaultModelVersion string = '2026-03-17'

@description('TPM capacity for default model deployment (in thousands). Keep modest to leave room for manual deploys in Lab 1.')
param defaultModelCapacity int = 20

@description('Embedding model name (used by Lab 03 hybrid retrieval).')
param embeddingModelName string = 'text-embedding-3-small'

@description('Embedding model version.')
param embeddingModelVersion string = '1'

@description('TPM capacity for the embedding model deployment (in thousands).')
param embeddingModelCapacity int = 30

@description('Deploy the realtime speech-to-speech model for the optional Lab 04 Voice Live demo. Leave false unless the subscription has realtime model quota.')
param deployRealtimeModel bool = false

@description('Realtime speech-to-speech model used by Lab 04 Voice Live demo. Deployed in the same Foundry account; reached via the project endpoint over WSS. Swap if your region does not carry this model — `gpt-realtime` and `gpt-4o-realtime-preview` are the other common choices.')
param realtimeModelName string = 'gpt-realtime-1.5'

@description('Realtime model version.')
param realtimeModelVersion string = '2026-02-23'

@description('TPM capacity for the realtime model deployment (in thousands). One concurrent voice session is enough for the instructor demo.')
param realtimeModelCapacity int = 10

@description('Resource ID of the Application Insights instance to connect to the project (so agent traces show up in Foundry Tracing).')
param appInsightsId string

@description('Connection string of the Application Insights instance. Used as the ApiKey credential on the project connection.')
@secure()
param appInsightsConnectionString string

#disable-next-line BCP037
resource foundry 'Microsoft.CognitiveServices/accounts@2026-03-01' = {
  name: 'foundry-${resourceToken}'
  location: location
  tags: tags
  kind: 'AIServices'
  sku: {
    name: 'S0'
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    customSubDomainName: 'foundry-${resourceToken}'
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: false
    #disable-next-line BCP037
    allowProjectManagement: true
  }
}

resource foundryProject 'Microsoft.CognitiveServices/accounts/projects@2026-03-01' = {
  parent: foundry
  name: 'noclar-assessment'
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    displayName: 'NOCLAR Initial Assessment'
    description: 'NOCLAR Initial Assessment Agent — AI Foundry Workshop'
  }
}

resource defaultModelDeployment 'Microsoft.CognitiveServices/accounts/deployments@2026-03-01' = {
  parent: foundry
  name: defaultModelName
  sku: {
    name: 'GlobalStandard'
    capacity: defaultModelCapacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: defaultModelName
      version: defaultModelVersion
    }
    raiPolicyName: 'Microsoft.DefaultV2'
  }
}

// Embedding model — used by Lab 03 to build the hybrid retrieval index over
// the sample-doc corpus. The embedding endpoint is reached via the same
// Foundry project endpoint as the chat model.
resource embeddingModelDeployment 'Microsoft.CognitiveServices/accounts/deployments@2026-03-01' = {
  parent: foundry
  name: embeddingModelName
  sku: {
    name: 'GlobalStandard'
    capacity: embeddingModelCapacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: embeddingModelName
      version: embeddingModelVersion
    }
  }
  dependsOn: [
    defaultModelDeployment
  ]
}

// Optional realtime speech-to-speech model for the Lab 04 Voice Live demo.
resource realtimeModelDeployment 'Microsoft.CognitiveServices/accounts/deployments@2026-03-01' = if (deployRealtimeModel) {
  parent: foundry
  name: realtimeModelName
  sku: {
    name: 'GlobalStandard'
    capacity: realtimeModelCapacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: realtimeModelName
      version: realtimeModelVersion
    }
    raiPolicyName: 'Microsoft.DefaultV2'
  }
  dependsOn: [
    embeddingModelDeployment
  ]
}

// Connect Application Insights to the Foundry project so agent runs, tool
// calls, and LLM spans appear in the portal's Tracing view (used in Lab 01).
#disable-next-line BCP037
resource appInsightsConnection 'Microsoft.CognitiveServices/accounts/projects/connections@2026-03-01' = {
  parent: foundryProject
  name: 'appinsights'
  properties: {
    category: 'AppInsights'
    target: appInsightsId
    authType: 'ApiKey'
    isSharedToAll: true
    metadata: {
      ApiType: 'Azure'
      ResourceId: appInsightsId
    }
    credentials: {
      key: appInsightsConnectionString
    }
  }
}

output foundryId string = foundry.id
output foundryName string = foundry.name
output foundryEndpoint string = foundry.properties.endpoint
output foundryPrincipalId string = foundry.identity.principalId
output projectName string = foundryProject.name
output projectId string = foundryProject.id
output projectEndpoint string = 'https://${foundry.name}.services.ai.azure.com/api/projects/${foundryProject.name}'
output projectPrincipalId string = foundryProject.identity.principalId
output defaultModelDeploymentName string = defaultModelDeployment.name
output embeddingModelDeploymentName string = embeddingModelDeployment.name
output realtimeModelDeploymentName string = deployRealtimeModel ? realtimeModelDeployment.name : ''
