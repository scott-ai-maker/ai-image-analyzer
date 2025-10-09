using 'main.bicep'

// Production environment parameters
param environmentName = 'prod'
param location = 'East US 2'
param projectName = 'ai-image-analyzer'

param appConfig = {
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

param skuConfig = {
  name: 'P1v3'
  tier: 'PremiumV3'
  capacity: 1
}
