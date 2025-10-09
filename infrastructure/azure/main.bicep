// Main Bicep template for AI Image Analyzer - Enterprise Full-Stack Deployment
targetScope = 'subscription'

@description('The name of the environment (e.g., dev, staging, prod)')
param environmentName string = 'prod'

@description('The Azure region where resources will be deployed')
param location string = 'East US 2'

@description('The base name for all resources')
param projectName string = 'ai-image-analyzer'

@description('Configuration for the application')
param appConfig object = {
  backend: {
    name: 'backend'
    runtime: 'PYTHON|3.11'
    alwaysOn: true
    httpsOnly: true
  }
  frontend: {
    name: 'frontend'
    runtime: 'NODE|18-lts'
    alwaysOn: true
    httpsOnly: true
  }
}

@description('SKU configuration for App Service Plan')
param skuConfig object = {
  name: 'P1v3'
  tier: 'PremiumV3'
  capacity: 1
}

// Variables
var resourceGroupName = '${projectName}-${environmentName}-rg'
var tags = {
  Environment: environmentName
  Project: projectName
  Owner: 'Enterprise-Demo'
  ManagedBy: 'Bicep'
}

// Resource Group
resource resourceGroup 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: resourceGroupName
  location: location
  tags: tags
}

// Deploy the main infrastructure
module infrastructure 'modules/infrastructure.bicep' = {
  scope: resourceGroup
  params: {
    projectName: projectName
    environmentName: environmentName
    location: location
    appConfig: appConfig
    skuConfig: skuConfig
    tags: tags
  }
}

// Outputs
output resourceGroupName string = resourceGroup.name
output backendUrl string = infrastructure.outputs.backendUrl
output frontendUrl string = infrastructure.outputs.frontendUrl
output applicationInsightsKey string = infrastructure.outputs.applicationInsightsKey
output logAnalyticsWorkspaceId string = infrastructure.outputs.logAnalyticsWorkspaceId
