using 'main.bicep'

// Development environment parameters
param environmentName = 'dev'
param location = 'East US 2'
param projectName = 'ai-image-analyzer'

param appConfig = {
  backend: {
    name: 'backend'
    runtime: 'PYTHON|3.11'
    alwaysOn: false
    httpsOnly: true
  }
  frontend: {
    name: 'frontend'
    runtime: 'NODE|18-lts'
    alwaysOn: false
    httpsOnly: true
  }
}

param skuConfig = {
  name: 'B1'
  tier: 'Basic'
  capacity: 1
}
