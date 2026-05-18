// Storage Account with workshop containers
// Containers:
//   sample-docs   — fictional NOCLAR corpus (Block 3)
//   assessments   — orchestrator state + persisted memos (Block 2, 4)
//   logs          — request log target for governance Function (Block 4)

@description('Resource name prefix / resourceToken')
param resourceToken string

@description('Azure region')
param location string

@description('Common tags')
param tags object

var storageName = take('st${replace(resourceToken, '-', '')}xxx', 24)

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageName
  location: location
  tags: tags
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    allowSharedKeyAccess: true // Functions Flex Consumption deployment still needs this in some scenarios
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    publicNetworkAccess: 'Enabled'
    networkAcls: {
      defaultAction: 'Allow'
      bypass: 'AzureServices'
    }
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storage
  name: 'default'
  properties: {
    deleteRetentionPolicy: {
      enabled: true
      days: 7
    }
  }
}

var containerNames = [
  'sample-docs'
  'assessments'
  'logs'
  'deploymentpackage' // used by Functions Flex Consumption
]

resource containers 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = [for name in containerNames: {
  parent: blobService
  name: name
  properties: {
    publicAccess: 'None'
  }
}]

resource queueService 'Microsoft.Storage/storageAccounts/queueServices@2023-05-01' = {
  parent: storage
  name: 'default'
}

resource reviewerQueue 'Microsoft.Storage/storageAccounts/queueServices/queues@2023-05-01' = {
  parent: queueService
  name: 'reviewer-inbox'
}

output storageId string = storage.id
output storageName string = storage.name
output storageBlobEndpoint string = storage.properties.primaryEndpoints.blob
output storageQueueEndpoint string = storage.properties.primaryEndpoints.queue
output deploymentContainerName string = 'deploymentpackage'
