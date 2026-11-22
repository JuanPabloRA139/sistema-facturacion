$ErrorActionPreference = 'Stop'
$archivo = Join-Path $PSScriptRoot '../database/dynamodb.json'
$tabla = Get-Content -LiteralPath $archivo -Raw | ConvertFrom-Json
if ($tabla.BillingMode -ne 'PAY_PER_REQUEST') { throw 'Revisar modo de capacidad' }
foreach ($par in @(@('entidad','HASH'), @('evento','RANGE'))) {
    $clave = @($tabla.KeySchema | Where-Object { $_.AttributeName -eq $par[0] -and $_.KeyType -eq $par[1] })
    if ($clave.Count -ne 1) { throw "Revisar clave $($par[0])" }
}
Write-Output "Esquema local correcto: $($tabla.TableName)"
