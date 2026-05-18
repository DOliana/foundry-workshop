// Azure AI Foundry account + project + o4-mini model deployment
// Used by: every block. This is the centerpiece of the workshop.
//
// Notes:
//   * Uses the unified AIServices kind (Foundry generation, GA in 2025)
//   * TPM cap on o4-mini is intentionally conservative so participants have
//     room to deploy additional models manually during Lab 1.

@description('Resource name prefix / resourceToken')
param resourceToken string

@description('Azure region (use swedencentral — that is where we have quota)')
param location string

@description('Common tags')
param tags object

@description('Model name for the default deployment')
param defaultModelName string = 'o4-mini'

@description('Model version for the default deployment')
param defaultModelVersion string = '2025-04-16'

@description('TPM capacity for default model deployment (in thousands). Keep modest to leave room for manual deploys in Lab 1.')
param defaultModelCapacity int = 20

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

output foundryId string = foundry.id
output foundryName string = foundry.name
output foundryEndpoint string = foundry.properties.endpoint
output foundryPrincipalId string = foundry.identity.principalId
output projectName string = foundryProject.name
output projectId string = foundryProject.id
output projectEndpoint string = 'https://${foundry.name}.services.ai.azure.com/api/projects/${foundryProject.name}'
output projectPrincipalId string = foundryProject.identity.principalId
output defaultModelDeploymentName string = defaultModelDeployment.name
