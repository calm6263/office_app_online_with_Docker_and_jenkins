import jenkins.model.*
import hudson.security.*

def jenkins = Jenkins.get()
def env = System.getenv()

def adminUsername = env['JENKINS_ADMIN_ID']
def adminPassword = env['JENKINS_ADMIN_PASSWORD']

if (!(adminUsername?.trim() && adminPassword?.trim())) {
    println "بيانات المدير غير محددة"
    return
}

def hudsonRealm = new HudsonPrivateSecurityRealm(false)
hudsonRealm.createAccount(adminUsername, adminPassword)
jenkins.setSecurityRealm(hudsonRealm)

def strategy = new FullControlOnceLoggedInAuthorizationStrategy()
jenkins.setAuthorizationStrategy(strategy)

jenkins.save()
println "تم إنشاء حساب المدير بنجاح"