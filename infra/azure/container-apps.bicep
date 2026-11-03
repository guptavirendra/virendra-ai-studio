targetScope = 'resourceGroup'

@description('Azure region for the Container App and migration job.')
param location string = resourceGroup().location

@description('Resource ID of an existing Azure Container Apps managed environment.')
param containerAppsEnvironmentId string

@description('Name of the production Container App.')
param appName string

@description('Name of the manual migration Container Apps job.')
param migrationJobName string

@description('Fully qualified login server of an existing Azure Container Registry.')
param registryServer string

@description('Backend image reference, including an immutable tag or digest.')
param backendImage string

@description('Production frontend image reference, including an immutable tag or digest.')
param frontendImage string

@description('Create/update the public app only after the migration job has succeeded.')
param deployApplication bool = false

@description('External public media URL used by publishing integrations, when configured.')
param publicMediaBaseUrl string = ''

@description('HTTPS Blob service endpoint for an existing storage account.')
param azureStorageAccountUrl string

@description('Name of an existing private Blob container for rendered media.')
param azureStorageContainer string = 'studio-media'

@description('Optional non-secret publishing integration configuration.')
param instagramUserId string = ''
param instagramGraphApiVersion string = 'v22.0'
param facebookPageId string = ''
param telegramChatId string = ''
param youtubeCategoryId string = '25'
param youtubePrivacyStatus string = 'private'

@secure()
@description('PostgreSQL connection string for the existing database.')
param databaseUrl string

@secure()
@description('Unique session-signing key; use at least 32 characters.')
param sessionSecretKey string

@secure()
@description('Bootstrap administrator username. The account is created only on an empty users table.')
param bootstrapAdminUsername string

@secure()
@description('Bootstrap administrator password; use a strong password of at least 12 characters.')
param bootstrapAdminPassword string

@secure()
@description('Optional OpenAI API key.')
param openAiApiKey string = ''

@secure()
@description('Optional Instagram access token.')
param instagramAccessToken string = ''

@secure()
@description('Optional Facebook Page access token.')
param facebookPageAccessToken string = ''

@secure()
@description('Optional Telegram bot token.')
param telegramBotToken string = ''

@secure()
@description('Optional YouTube OAuth client-secrets JSON content.')
param youtubeClientSecretsJson string = ''

@secure()
@description('Optional YouTube OAuth token JSON content.')
param youtubeTokenJson string = ''

var sharedSecrets = concat(
  [
    { name: 'database-url', value: databaseUrl }
    { name: 'session-secret-key', value: sessionSecretKey }
    { name: 'bootstrap-admin-username', value: bootstrapAdminUsername }
    { name: 'bootstrap-admin-password', value: bootstrapAdminPassword }
  ],
  empty(openAiApiKey) ? [] : [{ name: 'openai-api-key', value: openAiApiKey }],
  empty(instagramAccessToken) ? [] : [{ name: 'instagram-access-token', value: instagramAccessToken }],
  empty(facebookPageAccessToken) ? [] : [{ name: 'facebook-page-access-token', value: facebookPageAccessToken }],
  empty(telegramBotToken) ? [] : [{ name: 'telegram-bot-token', value: telegramBotToken }]
)

var backendEnvironment = concat(
  [
    { name: 'DATABASE_URL', secretRef: 'database-url' }
    { name: 'SESSION_SECRET_KEY', secretRef: 'session-secret-key' }
    { name: 'BOOTSTRAP_ADMIN_USERNAME', secretRef: 'bootstrap-admin-username' }
    { name: 'BOOTSTRAP_ADMIN_PASSWORD', secretRef: 'bootstrap-admin-password' }
    { name: 'SESSION_COOKIE_SECURE', value: 'true' }
    { name: 'INSTAGRAM_USER_ID', value: instagramUserId }
    { name: 'INSTAGRAM_GRAPH_API_VERSION', value: instagramGraphApiVersion }
    { name: 'FACEBOOK_PAGE_ID', value: facebookPageId }
    { name: 'TELEGRAM_CHAT_ID', value: telegramChatId }
    { name: 'PUBLIC_MEDIA_BASE_URL', value: publicMediaBaseUrl }
    { name: 'YOUTUBE_CATEGORY_ID', value: youtubeCategoryId }
    { name: 'YOUTUBE_PRIVACY_STATUS', value: youtubePrivacyStatus }
    { name: 'AZURE_STORAGE_ACCOUNT_URL', value: azureStorageAccountUrl }
    { name: 'AZURE_STORAGE_CONTAINER', value: azureStorageContainer }
  ],
  empty(openAiApiKey) ? [] : [{ name: 'OPENAI_API_KEY', secretRef: 'openai-api-key' }],
  empty(instagramAccessToken) ? [] : [{ name: 'INSTAGRAM_ACCESS_TOKEN', secretRef: 'instagram-access-token' }],
  empty(facebookPageAccessToken) ? [] : [{ name: 'FACEBOOK_PAGE_ACCESS_TOKEN', secretRef: 'facebook-page-access-token' }],
  empty(telegramBotToken) ? [] : [{ name: 'TELEGRAM_BOT_TOKEN', secretRef: 'telegram-bot-token' }],
  empty(youtubeClientSecretsJson) ? [] : [{ name: 'YOUTUBE_CLIENT_SECRETS', value: '/run/secrets/youtube/client_secrets.json' }],
  empty(youtubeTokenJson) ? [] : [{ name: 'YOUTUBE_TOKEN_JSON', value: '/run/secrets/youtube/token.json' }]
)

var youtubeSecretVolume = empty(youtubeClientSecretsJson) && empty(youtubeTokenJson)
  ? []
  : [
      {
        name: 'youtube-secrets'
        storageType: 'Secret'
        secrets: concat(
          empty(youtubeClientSecretsJson) ? [] : [{ secretRef: 'youtube-client-secrets', path: 'client_secrets.json' }],
          empty(youtubeTokenJson) ? [] : [{ secretRef: 'youtube-token-json', path: 'token.json' }]
        )
      }
    ]

var youtubeSecretMount = empty(youtubeClientSecretsJson) && empty(youtubeTokenJson)
  ? []
  : [{ volumeName: 'youtube-secrets', mountPath: '/run/secrets/youtube' }]

var appSecrets = concat(
  sharedSecrets,
  empty(youtubeClientSecretsJson) ? [] : [{ name: 'youtube-client-secrets', value: youtubeClientSecretsJson }],
  empty(youtubeTokenJson) ? [] : [{ name: 'youtube-token-json', value: youtubeTokenJson }]
)

resource migrationJob 'Microsoft.App/jobs@2024-03-01' = {
  name: migrationJobName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    environmentId: containerAppsEnvironmentId
    configuration: {
      triggerType: 'Manual'
      replicaTimeout: 1800
      replicaRetryLimit: 0
      manualTriggerConfig: {
        parallelism: 1
        replicaCompletionCount: 1
      }
      registries: [
        {
          server: registryServer
          identity: 'system'
        }
      ]
      secrets: sharedSecrets
    }
    template: {
      containers: [
        {
          name: 'migration'
          image: backendImage
          command: ['alembic']
          args: ['upgrade', 'head']
          env: [
            { name: 'DATABASE_URL', secretRef: 'database-url' }
            { name: 'SESSION_SECRET_KEY', secretRef: 'session-secret-key' }
          ]
          resources: {
            cpu: 1
            memory: '2Gi'
          }
        }
      ]
    }
  }
}

resource application 'Microsoft.App/containerApps@2024-03-01' = if (deployApplication) {
  name: appName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    managedEnvironmentId: containerAppsEnvironmentId
    configuration: {
      activeRevisionsMode: 'Single'
      registries: [
        {
          server: registryServer
          identity: 'system'
        }
      ]
      secrets: appSecrets
      ingress: {
        external: true
        targetPort: 8080
        transport: 'auto'
        allowInsecure: false
        traffic: [
          {
            latestRevision: true
            weight: 100
          }
        ]
      }
    }
    template: {
      containers: [
        {
          name: 'frontend'
          image: frontendImage
          resources: {
            cpu: any('0.25')
            memory: '0.5Gi'
          }
          probes: [
            {
              type: 'Readiness'
              httpGet: {
                path: '/'
                port: 8080
                scheme: 'HTTP'
              }
              periodSeconds: 10
            }
            {
              type: 'Liveness'
              httpGet: {
                path: '/'
                port: 8080
                scheme: 'HTTP'
              }
              initialDelaySeconds: 10
              periodSeconds: 30
            }
          ]
        }
        {
          name: 'backend'
          image: backendImage
          env: backendEnvironment
          resources: {
            cpu: 1
            memory: '2Gi'
          }
          probes: [
            {
              type: 'Readiness'
              httpGet: {
                path: '/api/health'
                port: 8000
                scheme: 'HTTP'
              }
              periodSeconds: 10
            }
            {
              type: 'Liveness'
              httpGet: {
                path: '/api/health'
                port: 8000
                scheme: 'HTTP'
              }
              initialDelaySeconds: 10
              periodSeconds: 30
            }
          ]
          volumeMounts: youtubeSecretMount
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 3
      }
      volumes: youtubeSecretVolume
    }
  }
}
