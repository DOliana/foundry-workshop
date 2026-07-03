// RBAC role assignments — pre-wired so labs don't fight auth.
//
//   Deploying user → Cognitive Services User on Foundry (chat with agents)
//   Deploying user → Search Index Data Contributor on AI Search
//   Deploying user → Storage Blob Data Contributor on Storage
//   Functions MI    → Cognitive Services User on Foundry
//   Functions MI    → Search Index Data Contributor on AI Search
//   Functions MI    → Storage Blob Data Owner on Storage
//   Functions MI    → Storage Queue Data Contributor on Storage
//   Foundry MI      → Search Index Data Contributor + Service Contributor on AI Search
//   Foundry MI      → Storage Blob Data Reader on Storage
//   Foundry project MI → Search Index Data Contributor on AI Search (project-MI connections)
//   Search MI       → Cognitive Services User on Foundry (vectorizer)

@description('Principal ID of the deploying user')
param principalId string

@description('Principal ID of the Functions app system-assigned MI')
param functionsPrincipalId string

@description('Principal ID of the Foundry account system-assigned MI')
param foundryPrincipalId string

@description('Principal ID of the Foundry *project* system-assigned MI (used when a Foundry connection authenticates as "project managed identity")')
param foundryProjectPrincipalId string

@description('Principal ID of the AI Search service system-assigned MI')
param searchPrincipalId string

@description('Foundry account name')
param foundryName string

@description('AI Search service name')
param searchName string

@description('Storage account name')
param storageName string

// Built-in role definition IDs (GUIDs)
var roles = {
  cognitiveServicesUser:        'a97b65f3-24c7-4388-baec-2e87135dc908'
  cognitiveServicesContributor: '25fbc0a9-bd7c-42a3-aa1a-3b75d497ee68'
  searchIndexDataContributor:   '8ebe5a00-799e-43f5-93ac-243d3dce84a7'
  searchIndexDataReader:        '1407120a-92aa-4202-b7e9-c0e197c71c8f'
  searchServiceContributor:     '7ca78c08-252a-4471-8644-bb5ff32d4ba0'
  storageBlobDataOwner:         'b7e6dc6d-f1e8-4753-8033-0f276bb0955b'
  storageBlobDataContributor:   'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
  storageBlobDataReader:        '2a2b9908-6ea1-4ae2-8e65-a410df84e7d1'
  storageQueueDataContributor:  '974c5e8b-45b9-4653-ba55-5f855dd0fb88'
}

resource foundry 'Microsoft.CognitiveServices/accounts@2026-03-01' existing = {
  name: foundryName
}

resource search 'Microsoft.Search/searchServices@2024-06-01-preview' existing = {
  name: searchName
}

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: storageName
}

// ---------- Deploying user ----------

resource userFoundry 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(principalId)) {
  scope: foundry
  name: guid(foundry.id, principalId, roles.cognitiveServicesUser)
  properties: {
    principalId: principalId
    principalType: 'User'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.cognitiveServicesUser)
  }
}

resource userSearchData 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(principalId)) {
  scope: search
  name: guid(search.id, principalId, roles.searchIndexDataContributor)
  properties: {
    principalId: principalId
    principalType: 'User'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.searchIndexDataContributor)
  }
}

resource userSearchService 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(principalId)) {
  scope: search
  name: guid(search.id, principalId, roles.searchServiceContributor)
  properties: {
    principalId: principalId
    principalType: 'User'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.searchServiceContributor)
  }
}

resource userStorage 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(principalId)) {
  scope: storage
  name: guid(storage.id, principalId, roles.storageBlobDataContributor)
  properties: {
    principalId: principalId
    principalType: 'User'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.storageBlobDataContributor)
  }
}

// ---------- Functions MI ----------

resource fnFoundry 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: foundry
  name: guid(foundry.id, functionsPrincipalId, roles.cognitiveServicesUser)
  properties: {
    principalId: functionsPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.cognitiveServicesUser)
  }
}

resource fnSearchData 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: search
  name: guid(search.id, functionsPrincipalId, roles.searchIndexDataContributor)
  properties: {
    principalId: functionsPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.searchIndexDataContributor)
  }
}

resource fnStorageBlob 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: storage
  name: guid(storage.id, functionsPrincipalId, roles.storageBlobDataOwner)
  properties: {
    principalId: functionsPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.storageBlobDataOwner)
  }
}

resource fnStorageQueue 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: storage
  name: guid(storage.id, functionsPrincipalId, roles.storageQueueDataContributor)
  properties: {
    principalId: functionsPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.storageQueueDataContributor)
  }
}

// ---------- Foundry MI ----------

resource foundrySearchData 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: search
  name: guid(search.id, foundryPrincipalId, roles.searchIndexDataContributor)
  properties: {
    principalId: foundryPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.searchIndexDataContributor)
  }
}

resource foundrySearchService 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: search
  name: guid(search.id, foundryPrincipalId, roles.searchServiceContributor)
  properties: {
    principalId: foundryPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.searchServiceContributor)
  }
}

resource foundryStorage 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: storage
  name: guid(storage.id, foundryPrincipalId, roles.storageBlobDataReader)
  properties: {
    principalId: foundryPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.storageBlobDataReader)
  }
}

// ---------- Foundry project MI ----------
// When a Foundry connection to AI Search is created with auth =
// "project managed identity", the *project's* MI (distinct from the
// account MI) makes the query-time call to the search service. Without
// this role assignment the agent gets a 403 "credential is forbidden"
// even though the parent account MI is fully permitted.
//
// Contributor (not Reader) — Reader is technically sufficient for
// /docs/search, but in practice we've seen Foundry connections return
// 403 with Reader on the project MI; Contributor avoids the issue and
// the project MI cannot manipulate index *definitions* anyway (that's
// `Search Service Contributor`, which we don't grant here).
resource foundryProjectSearchData 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: search
  name: guid(search.id, foundryProjectPrincipalId, roles.searchIndexDataContributor)
  properties: {
    principalId: foundryProjectPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.searchIndexDataContributor)
  }
}

// ---------- AI Search MI ----------
// The vectorizer attached to the index's vector profile calls the Foundry
// embedding deployment at query time to embed the user's question; Foundry
// only enables Vector / Hybrid query modes when the profile has a vectorizer.
resource searchFoundry 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: foundry
  name: guid(foundry.id, searchPrincipalId, roles.cognitiveServicesUser)
  properties: {
    principalId: searchPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.cognitiveServicesUser)
  }
}
