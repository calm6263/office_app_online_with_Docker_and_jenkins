import jenkins.model.*
import hudson.model.*
import hudson.plugins.*
import hudson.tools.*
import jenkins.plugins.slack.*

def jenkins = Jenkins.instance

// تثبيت البلجنز الضرورية
def plugins = [
    'workflow-aggregator',
    'docker-workflow',
    'git',
    'slack',
    'junit'
]

def pluginManager = jenkins.pluginManager
def uc = jenkins.updateCenter

plugins.each { plugin ->
    if (!pluginManager.getPlugin(plugin)) {
        println "جارٍ تثبيت ${plugin}..."
        def install = uc.getPlugin(plugin).deploy()
        install.get()
    }
}

// إعداد Docker
def dockerTool = new DockerTool(
    "Docker",
    "/usr/bin/docker",
    null
)

def toolDesc = jenkins.getDescriptorByType(DockerTool.DescriptorImpl.class)
toolDesc.setInstallations(dockerTool)

// إعداد Slack
def slack = jenkins.getDescriptorByType(SlackNotifier.Descriptor.class)
slack.tokenCredentialId = "slack-token"
slack.baseUrl = "https://slack.com/api/"
slack.teamDomain = "your-team-domain"

jenkins.save()