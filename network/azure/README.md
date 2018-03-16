Commands to deploy:
https://azure.microsoft.com/en-us/resources/templates/docker-simple-on-ubuntu/

Login-AzureRmAccount -Subscription <subscription>
New-AzureRmResourceGroupDeployment -Name 'hashblock' -ResourceGroupName 'hashblock' -TemplateFile '.\templates\network-template.json' -TemplateParameterFile '.\parameters\dev\network-parameters.json' 