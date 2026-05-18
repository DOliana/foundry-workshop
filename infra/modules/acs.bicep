// Azure Communication Services — for Voice Live SDK demo (Block 4)
//
// Note: no phone number is provisioned (procurement lead time). The voice
// demo uses browser mic → Voice Live API → agent.

@description('Resource name prefix / resourceToken')
param resourceToken string

@description('Common tags')
param tags object

resource acs 'Microsoft.Communication/communicationServices@2023-04-01' = {
  name: 'acs-${resourceToken}'
  location: 'global'
  tags: tags
  properties: {
    dataLocation: 'Europe'
  }
}

output acsId string = acs.id
output acsName string = acs.name
output acsEndpoint string = acs.properties.hostName
