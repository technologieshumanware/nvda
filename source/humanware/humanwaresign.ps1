# Script used to sign assemblies from our Azure keyvault.
param (
    [string]$directory,
    [string]$fileName
)

$username = "username_placeholder"
$password = "password_placeholder"
$publisherName = "publisherName_placeholder"
$descriptionUrl = "decsriptionUrl_placeholder"
$tenantId = "tenantId_placeholder"
$certificate = "certificate_placeholder"
$vaultUrl = "vaultUrl_placeholder"

try {
    write-host "Signing $directory\$fileName"

    dotnet tool run sign code azure-key-vault "${fileName}" -v DEBUG `
        --base-directory "${directory}" `
        --output "${directory}" `
        --publisher-name $publisherName `
        --description $publisherName `
        --description-url $descriptionUrl `
        --azure-key-vault-tenant-id $tenantId `
        --azure-key-vault-client-id $username  `
        --azure-key-vault-client-secret $password `
        --azure-key-vault-certificate $certificate `
        --azure-key-vault-url $vaultUrl
}
catch {
    write-host $_.Exception.Message
    exit $LASTEXITCODE
}
