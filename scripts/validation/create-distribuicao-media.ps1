$ErrorActionPreference = "Stop"

$Origin = "http://127.0.0.1:8000"
$CredentialPath = Join-Path $env:LOCALAPPDATA "Clicko\credentials\local-owner.credential.clixml"
$ArtifactRoot = "C:\Users\edugu\Downloads\res\artifacts\validation"
$SourceVideoPath = Join-Path $ArtifactRoot "sources\pexels-7480852-content-creator.mp4"
$MusicPath = Join-Path $ArtifactRoot "sources\mixkit-1167-close-up.mp3"
$RunId = Get-Date -Format "yyyyMMdd-HHmmssfff"

function ConvertTo-ApiJson($Value) {
    return $Value | ConvertTo-Json -Depth 40 -Compress
}

function Wait-StudioJob([string] $JobId) {
    for ($attempt = 0; $attempt -lt 180; $attempt++) {
        $job = Invoke-RestMethod -Uri "$Origin/api/v1/studios/v1/jobs/$JobId" -Headers $script:Headers
        if ($job.status -in @("succeeded", "failed", "cancelled")) {
            return $job
        }
        Start-Sleep -Seconds 1
    }
    throw "studio_job_timeout:$JobId"
}

function Upload-Asset([string] $Path, [string] $Title, [string] $MediaType) {
    $response = & curl.exe -sS --fail-with-body -X POST `
        -H "Authorization: $($script:Headers.Authorization)" `
        -F "workspace_id=$script:WorkspaceId" `
        -F "title=$Title" `
        -F "file=@$Path;type=$MediaType" `
        "$Origin/api/v1/assets/upload"
    if ($LASTEXITCODE -ne 0) {
        throw "asset_upload_failed:$Title"
    }
    return $response | ConvertFrom-Json
}

function Ingest-Asset($Asset, [string] $IdempotencyKey) {
    $headers = @{
        Authorization = $script:Headers.Authorization
        "Idempotency-Key" = $IdempotencyKey
    }
    $ingest = Invoke-RestMethod -Method Post `
        -Uri "$Origin/api/v1/studios/v1/media-ingests" `
        -Headers $headers `
        -ContentType "application/json" `
        -Body (ConvertTo-ApiJson @{ workspaceId = $script:WorkspaceId; assetId = $Asset.id })
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        if ($ingest.status -in @("ready", "failed", "rejected")) {
            break
        }
        Start-Sleep -Milliseconds 500
        $ingest = Invoke-RestMethod `
            -Uri "$Origin/api/v1/studios/v1/media-ingests/$($ingest.id)" `
            -Headers $script:Headers
    }
    if ($ingest.status -ne "ready") {
        throw "media_ingest_failed:$($ingest.status):$($ingest.validationErrors -join ',')"
    }
    return $ingest
}

function Review-MusicRights($Document, $Music, [string] $IdempotencyKey) {
    $headers = @{
        Authorization = $script:Headers.Authorization
        "Idempotency-Key" = $IdempotencyKey
    }
    $body = @{
        expectedDocumentRevision = $Document.revision
        assetChecksumSha256 = $Music.checksumSha256
        decision = "verified"
        basis = "open-license"
        sourceReference = "https://mixkit.co/free-stock-music/corporate-music/"
        rightsReference = "https://mixkit.co/license/#musicFree"
        noExpirationConfirmed = $true
        notes = "Track Close Up, item 1167; Clicko validation render."
    }
    return Invoke-RestMethod -Method Post `
        -Uri "$Origin/api/v1/studios/v1/documents/$($Document.documentId)/assets/$($Music.id)/rights-reviews" `
        -Headers $headers `
        -ContentType "application/json" `
        -Body (ConvertTo-ApiJson $body)
}

function New-UgcDocument($Source, $Music) {
    $fps = 25
    $frames = 300
    $durationMicroseconds = 12000000
    $pageLayers = @(
        @{
            id = "top-shade"; kind = "shape"; name = "Contraste superior"
            x = 48; y = 72; width = 984; height = 300; zIndex = 10
            properties = @{ type = "shape"; shape = "rectangle"; fill = "#080B12"; radius = 38 }
        },
        @{
            id = "hook"; kind = "text"; name = "Hook"
            x = 96; y = 116; width = 888; height = 210; zIndex = 11
            properties = @{
                type = "text"; text = "VOCÊ CRIA.`nMAS DISTRIBUI?"
                fontSize = 72; minFontSize = 48; fontFamily = "Liberation Sans"
                fontWeight = "bold"; color = "#FFFFFF"; align = "left"; lineHeight = 1.0
            }
        },
        @{
            id = "cta-band"; kind = "shape"; name = "Faixa CTA"
            x = 72; y = 1648; width = 936; height = 166; zIndex = 12
            properties = @{ type = "shape"; shape = "rectangle"; fill = "#6C5CE7"; radius = 36 }
        },
        @{
            id = "cta"; kind = "text"; name = "CTA"
            x = 120; y = 1687; width = 840; height = 92; zIndex = 13
            properties = @{
                type = "text"; text = "DISTRIBUA COM A CLICKO"
                fontSize = 48; minFontSize = 32; fontFamily = "Liberation Sans"
                fontWeight = "bold"; color = "#FFFFFF"; align = "center"; lineHeight = 1.0
            }
        }
    )
    $captionStyle = @{
        preset = "brand-bold"; color = "#FFFFFF"; outlineColor = "#000000"
        outlineWidth = 5; maxLines = 2
    }
    $captionCues = @(
        @{ id = "cap-1"; timeline = @{ startFrame = 0; durationFrames = 50 }; text = "VOCÊ CRIA."; style = $captionStyle + @{ fontSize = 58 } },
        @{ id = "cap-2"; timeline = @{ startFrame = 50; durationFrames = 50 }; text = "MAS DISTRIBUI?"; style = $captionStyle + @{ fontSize = 58 } },
        @{ id = "cap-3"; timeline = @{ startFrame = 100; durationFrames = 75 }; text = "UMA IDEIA. CINCO FORMATOS."; style = $captionStyle + @{ fontSize = 54; emphasisColor = "#6C5CE7" } },
        @{ id = "cap-4"; timeline = @{ startFrame = 175; durationFrames = 75 }; text = "VÍDEO. CARROSSEL. POST. CLIPES."; style = $captionStyle + @{ fontSize = 48 } },
        @{ id = "cap-5"; timeline = @{ startFrame = 250; durationFrames = 50 }; text = "CLICKO DISTRIBUI. VOCÊ CRESCE."; style = $captionStyle + @{ fontSize = 50; emphasisColor = "#6C5CE7" } }
    )
    $tracks = @(
        @{
            id = "video-main"; kind = "video"; name = "Criadora em estúdio"; muted = $true
            clips = @(@{
                id = "ugc-source"; assetId = $Source.id
                timeline = @{ startFrame = 0; durationFrames = $frames }
                source = @{ startMicroseconds = 0; durationMicroseconds = $durationMicroseconds }
                transform = @{ fit = "cover"; anchor = "center" }
            })
        },
        @{
            id = "music-main"; kind = "audio"; name = "Close Up — Mixkit"; muted = $false
            clips = @(@{
                id = "music-close-up"; assetId = $Music.id
                timeline = @{ startFrame = 0; durationFrames = $frames }
                source = @{ startMicroseconds = 0; durationMicroseconds = $durationMicroseconds }
                gainDb = -14; fadeInFrames = 12; fadeOutFrames = 20
            })
        },
        @{
            id = "captions-main"; kind = "caption"; name = "Mensagem editorial"
            locale = "pt-BR"; cues = $captionCues
        }
    )
    $body = @{
        workspaceId = $script:WorkspaceId
        title = "UGC — Distribuição de conteúdo"
        contentType = "video"
        brandRevision = 1
        correlationId = "distribuicao-ugc-20260831"
        brief = @{
            objective = "Mostrar que criar é apenas metade do trabalho: a Clicko distribui cada ideia em múltiplos formatos"
            audience = "Criadores, marcas e equipes de conteúdo"
            angle = "Da criação isolada para um sistema de distribuição"
            promise = "Uma ideia vira presença contínua em vários formatos"
            hook = "Você cria. Mas distribui?"
            cta = "Distribua com a Clicko"
            channel = "instagram"; format = "reel"; tone = "direto, energético e editorial"
            restrictions = @("sem voz", "sem alegação de endosso da pessoa retratada")
            hypotheses = @("clareza de distribuição aumenta intenção de teste")
        }
        composition = @{
            narrative = @{
                mode = "ugc-assisted"; sourceAssetId = $Source.id; originalPreserved = $true
                audioMode = "licensed-music-and-natural-sfx"; voicePolicy = "prohibited"
                musicPolicy = "licensed-with-rights"; captionMode = "editorial-burned-in"
                distributionTheme = "content-distribution"
            }
            pages = @(@{
                id = "ugc-distribuicao"; role = "ugc-main"; width = 1080; height = 1920
                durationMs = 12000; safeArea = 72; background = "#080B12"; layers = $pageLayers
            })
            mediaTimeline = @{
                frameRate = @{ numerator = $fps; denominator = 1 }
                durationFrames = $frames; tracks = $tracks
            }
        }
        assets = @(
            @{
                id = $Source.id; mediaType = $Source.mediaType; checksum = $Source.checksumSha256
                rightsStatus = "verified"
                provenance = @{
                    source = "user-upload"; sourceDeclaration = "Pexels video 7480852 by MART PRODUCTION"
                    licenseDeclaration = "Pexels License, free use with modification; no endorsement implied"
                    sourceReference = "https://www.pexels.com/video/7480852/"
                }
            },
            @{
                id = $Music.id; mediaType = $Music.mediaType; checksum = $Music.checksumSha256
                rightsStatus = "unknown"
                provenance = @{
                    purpose = "licensed-music-candidate"; source = "user-upload"
                    sourceDeclaration = "Mixkit track 1167 Close Up by Michael Ramir C."
                    licenseDeclaration = "Mixkit Stock Music Free License"
                    sourceReference = "https://mixkit.co/free-stock-music/corporate-music/"
                    licenseReference = "https://mixkit.co/license/#musicFree"
                }
            }
        )
    }
    return Invoke-RestMethod -Method Post `
        -Uri "$Origin/api/v1/studios/v1/documents" `
        -Headers $script:Headers `
        -ContentType "application/json" `
        -Body (ConvertTo-ApiJson $body)
}

function New-MotionDocument($Music) {
    $frames = 250
    $durationMicroseconds = 10000000
    $layers = @(
        @{
            id = "bg"; kind = "shape"; name = "Fundo"
            x = 0; y = 0; width = 1080; height = 1920; zIndex = 0
            properties = @{ shape = "rectangle"; fill = "#211B42"; radius = 0 }
        },
        @{
            id = "signal"; kind = "shape"; name = "Sinal central"
            x = 450; y = 780; width = 180; height = 180; zIndex = 2
            properties = @{ shape = "ellipse"; fill = "#6C5CE7"; radius = 90 }
        },
        @{
            id = "title"; kind = "text"; name = "Título"
            x = 90; y = 190; width = 900; height = 200; zIndex = 4
            properties = @{ text = "DISTRIBUIÇÃO"; fontSize = 94; minFontSize = 38; fontFamily = "Liberation Sans"; fontWeight = "bold"; color = "#FFFFFF"; align = "center"; lineHeight = 1.0 }
        },
        @{
            id = "promise"; kind = "text"; name = "Promessa"
            x = 120; y = 390; width = 840; height = 170; zIndex = 4
            properties = @{ text = "UMA IDEIA. MÚLTIPLOS FORMATOS."; fontSize = 46; minFontSize = 26; fontFamily = "Liberation Sans"; fontWeight = "bold"; color = "#B8B5FF"; align = "center"; lineHeight = 1.05 }
        },
        @{
            id = "node-video"; kind = "text"; name = "Nó Vídeo"
            x = 92; y = 710; width = 340; height = 120; zIndex = 5
            properties = @{ text = "VÍDEO"; fontSize = 54; minFontSize = 28; fontFamily = "Liberation Sans"; fontWeight = "bold"; color = "#FFFFFF"; align = "center"; lineHeight = 1.0 }
        },
        @{
            id = "node-post"; kind = "text"; name = "Nó Post"
            x = 648; y = 710; width = 340; height = 120; zIndex = 5
            properties = @{ text = "POST"; fontSize = 54; minFontSize = 28; fontFamily = "Liberation Sans"; fontWeight = "bold"; color = "#FFFFFF"; align = "center"; lineHeight = 1.0 }
        },
        @{
            id = "node-carousel"; kind = "text"; name = "Nó Carrossel"
            x = 56; y = 1050; width = 430; height = 120; zIndex = 5
            properties = @{ text = "CARROSSEL"; fontSize = 48; minFontSize = 24; fontFamily = "Liberation Sans"; fontWeight = "bold"; color = "#FFFFFF"; align = "center"; lineHeight = 1.0 }
        },
        @{
            id = "node-clips"; kind = "text"; name = "Nó Clipes"
            x = 594; y = 1050; width = 430; height = 120; zIndex = 5
            properties = @{ text = "CLIPES"; fontSize = 52; minFontSize = 26; fontFamily = "Liberation Sans"; fontWeight = "bold"; color = "#FFFFFF"; align = "center"; lineHeight = 1.0 }
        },
        @{
            id = "cta-motion"; kind = "text"; name = "CTA"
            x = 100; y = 1530; width = 880; height = 190; zIndex = 6
            properties = @{ text = "CRIE UMA VEZ.`nDISTRIBUA SEM PARAR."; fontSize = 64; minFontSize = 32; fontFamily = "Liberation Sans"; fontWeight = "bold"; color = "#FFFFFF"; align = "center"; lineHeight = 1.05 }
        }
    )
    $body = @{
        workspaceId = $script:WorkspaceId
        title = "Motion — Distribuição de conteúdo"
        contentType = "video"
        brandRevision = 1
        correlationId = "distribuicao-motion-20260831"
        brief = @{
            objective = "Explicar distribuição de conteúdo como expansão visual de uma ideia para vários formatos"
            audience = "Criadores, marcas e equipes de conteúdo"
            angle = "Um núcleo criativo se transforma em presença multiformato"
            promise = "Crie uma vez e distribua sem parar"
            hook = "Distribuição multiplica a criação"
            cta = "Crie uma vez. Distribua sem parar."
            channel = "instagram"; format = "reel-motion"; tone = "gráfico, tecnológico e direto"
            restrictions = @("sem voz", "sem física implícita em elementos abstratos")
            hypotheses = @("expansão radial comunica distribuição em menos de três segundos")
        }
        composition = @{
            narrative = @{
                mode = "motion-graphic"; voicePolicy = "prohibited"
                musicPolicy = "licensed-with-rights"; distributionTheme = "content-distribution"
                motionSemantics = "graphic-network-expansion"
            }
            pages = @(@{
                id = "motion-distribuicao"; role = "motion-main"; width = 1080; height = 1920
                durationMs = 10000; safeArea = 72; background = "#211B42"; layers = $layers
            })
            mediaTimeline = @{
                frameRate = @{ numerator = 25; denominator = 1 }
                durationFrames = $frames
                tracks = @(@{
                    id = "music-motion"; kind = "audio"; name = "Close Up — Mixkit"; muted = $false
                    clips = @(@{
                        id = "music-motion-close-up"; assetId = $Music.id
                        timeline = @{ startFrame = 0; durationFrames = $frames }
                        source = @{ startMicroseconds = 12000000; durationMicroseconds = $durationMicroseconds }
                        gainDb = -13; fadeInFrames = 12; fadeOutFrames = 24
                    })
                })
            }
        }
        assets = @(@{
            id = $Music.id; mediaType = $Music.mediaType; checksum = $Music.checksumSha256
            rightsStatus = "unknown"
            provenance = @{
                purpose = "licensed-music-candidate"; source = "user-upload"
                sourceDeclaration = "Mixkit track 1167 Close Up by Michael Ramir C."
                licenseDeclaration = "Mixkit Stock Music Free License"
                sourceReference = "https://mixkit.co/free-stock-music/corporate-music/"
                licenseReference = "https://mixkit.co/license/#musicFree"
            }
        })
    }
    return Invoke-RestMethod -Method Post `
        -Uri "$Origin/api/v1/studios/v1/documents" `
        -Headers $script:Headers `
        -ContentType "application/json" `
        -Body (ConvertTo-ApiJson $body)
}

function New-MotionGraph($Document) {
    $tracks = @(
        @{ trackId = "title-y"; targetLayerId = "title"; property = "position_y"; unit = "pixels"; keyframes = @(@{ frame = 0; value = -220; easing = "ease_out" }, @{ frame = 30; value = 0; easing = "linear" }) },
        @{ trackId = "promise-opacity"; targetLayerId = "promise"; property = "opacity"; unit = "ratio"; keyframes = @(@{ frame = 20; value = 0; easing = "ease_out" }, @{ frame = 48; value = 1; easing = "linear" }) },
        @{ trackId = "signal-scale-x"; targetLayerId = "signal"; property = "scale_x"; unit = "ratio"; keyframes = @(@{ frame = 35; value = 0.05; easing = "ease_out" }, @{ frame = 68; value = 1; easing = "linear" }) },
        @{ trackId = "signal-scale-y"; targetLayerId = "signal"; property = "scale_y"; unit = "ratio"; keyframes = @(@{ frame = 35; value = 0.05; easing = "ease_out" }, @{ frame = 68; value = 1; easing = "linear" }) },
        @{ trackId = "video-x"; targetLayerId = "node-video"; property = "position_x"; unit = "pixels"; keyframes = @(@{ frame = 70; value = 260; easing = "ease_out" }, @{ frame = 105; value = 0; easing = "linear" }) },
        @{ trackId = "video-opacity"; targetLayerId = "node-video"; property = "opacity"; unit = "ratio"; keyframes = @(@{ frame = 70; value = 0; easing = "ease_out" }, @{ frame = 105; value = 1; easing = "linear" }) },
        @{ trackId = "post-x"; targetLayerId = "node-post"; property = "position_x"; unit = "pixels"; keyframes = @(@{ frame = 78; value = -260; easing = "ease_out" }, @{ frame = 113; value = 0; easing = "linear" }) },
        @{ trackId = "post-opacity"; targetLayerId = "node-post"; property = "opacity"; unit = "ratio"; keyframes = @(@{ frame = 78; value = 0; easing = "ease_out" }, @{ frame = 113; value = 1; easing = "linear" }) },
        @{ trackId = "carousel-x"; targetLayerId = "node-carousel"; property = "position_x"; unit = "pixels"; keyframes = @(@{ frame = 86; value = 290; easing = "ease_out" }, @{ frame = 121; value = 0; easing = "linear" }) },
        @{ trackId = "carousel-opacity"; targetLayerId = "node-carousel"; property = "opacity"; unit = "ratio"; keyframes = @(@{ frame = 86; value = 0; easing = "ease_out" }, @{ frame = 121; value = 1; easing = "linear" }) },
        @{ trackId = "clips-x"; targetLayerId = "node-clips"; property = "position_x"; unit = "pixels"; keyframes = @(@{ frame = 94; value = -290; easing = "ease_out" }, @{ frame = 129; value = 0; easing = "linear" }) },
        @{ trackId = "clips-opacity"; targetLayerId = "node-clips"; property = "opacity"; unit = "ratio"; keyframes = @(@{ frame = 94; value = 0; easing = "ease_out" }, @{ frame = 129; value = 1; easing = "linear" }) },
        @{ trackId = "cta-opacity"; targetLayerId = "cta-motion"; property = "opacity"; unit = "ratio"; keyframes = @(@{ frame = 145; value = 0; easing = "ease_out" }, @{ frame = 180; value = 1; easing = "linear" }) },
        @{ trackId = "cta-y"; targetLayerId = "cta-motion"; property = "position_y"; unit = "pixels"; keyframes = @(@{ frame = 145; value = 180; easing = "ease_out" }, @{ frame = 180; value = 0; easing = "linear" }) }
    )
    $constraint = @{
        constraintId = "distribution-no-overshoot"
        kind = "no_overshoot"
        targetTrackIds = @($tracks | ForEach-Object { $_.trackId })
        frameRange = @{ startFrame = 0; endFrameExclusive = 181 }
        severity = "blocking"
    }
    $graph = @{
        graphId = "distribution-motion-$RunId"
        workspaceId = $script:WorkspaceId
        documentId = $Document.documentId
        documentRevision = $Document.revision
        frameRate = @{ numerator = 25; denominator = 1 }
        durationFrames = 250
        canvasWidth = 1080; canvasHeight = 1920
        realityMode = "graphic"; completeness = "complete"; status = "suggested"
        tracks = $tracks; constraints = @($constraint)
        sourceEvidenceIds = @(); abstentions = @()
        createdBy = "clicko.motion-planner.v1"
        humanReviewRequired = $true
        createdAt = (Get-Date).ToUniversalTime().ToString("o")
    }
    $created = Invoke-RestMethod -Method Post `
        -Uri "$Origin/api/v1/studios/v1/motion-graphs" `
        -Headers $script:Headers `
        -ContentType "application/json" `
        -Body (ConvertTo-ApiJson @{
            workspaceId = $script:WorkspaceId
            graph = $graph
            idempotencyKey = "distribution-motion-create-$RunId"
        })
    return Invoke-RestMethod -Method Post `
        -Uri "$Origin/api/v1/studios/v1/motion-graphs/$($created.graph.graphId)/review" `
        -Headers $script:Headers `
        -ContentType "application/json" `
        -Body (ConvertTo-ApiJson @{
            workspaceId = $script:WorkspaceId
            expectedRevision = $created.storageRevision
        })
}

$credential = Import-Clixml $CredentialPath
$login = Invoke-RestMethod -Method Post `
    -Uri "$Origin/api/v1/auth/login" `
    -ContentType "application/json" `
    -Body (ConvertTo-ApiJson @{
        email = $credential.UserName
        password = $credential.GetNetworkCredential().Password
    })
$script:Headers = @{ Authorization = "Bearer $($login.accessToken)" }
$bootstrap = Invoke-RestMethod -Uri "$Origin/api/v1/bootstrap" -Headers $script:Headers
$script:WorkspaceId = $bootstrap.workspaces[0].id

$source = Upload-Asset $SourceVideoPath "UGC Distribuição — fonte Pexels 7480852" "video/mp4"
$music = Upload-Asset $MusicPath "Trilha Distribuição — Close Up (Mixkit 1167)" "audio/mpeg"
$sourceIngest = Ingest-Asset $source "dist-ugc-source-ingest-$RunId"
$musicIngest = Ingest-Asset $music "dist-music-ingest-$RunId"
$ugcDocument = New-UgcDocument $source $music
$ugcRights = Review-MusicRights $ugcDocument $music "dist-music-rights-ugc-$RunId"
$ugcDocument = $ugcRights.document
$ugcRenderRequest = @{
    workspaceId = $script:WorkspaceId
    documentId = $ugcDocument.documentId
    expectedDocumentRevision = $ugcDocument.revision
    expectedDocumentVersion = $ugcDocument.version
    pageIds = @("ugc-distribuicao")
    provider = "builtin.ffmpeg-ugc-v1"
    output = @{
        format = "mp4"; width = 1080; height = 1920; fps = 25
        videoCodec = "h264"; audioCodec = "aac"; quality = "draft"
    }
    correlationId = "distribuicao-ugc-render-20260831"
}
$ugcJob = Invoke-RestMethod -Method Post `
    -Uri "$Origin/api/v1/studios/v1/video-renders" `
    -Headers @{ Authorization = $script:Headers.Authorization; "Idempotency-Key" = "dist-ugc-render-$RunId" } `
    -ContentType "application/json" `
    -Body (ConvertTo-ApiJson $ugcRenderRequest)
$ugcJob = Wait-StudioJob $ugcJob.id
if ($ugcJob.status -ne "succeeded") {
    throw "ugc_render_failed:$($ugcJob.errorCode):$($ugcJob.errorMessage)"
}
$ugcOutput = Join-Path $ArtifactRoot "distribuicao-ugc-clicko.mp4"
Invoke-WebRequest `
    -Uri "$Origin$($ugcJob.result.artifact.storageUri)" `
    -Headers $script:Headers `
    -OutFile $ugcOutput

$motionDocument = New-MotionDocument $music
$motionRights = Review-MusicRights $motionDocument $music "dist-music-rights-motion-$RunId"
$motionDocument = $motionRights.document
$motionGraph = New-MotionGraph $motionDocument
$motionState = @{
    workspaceId = $script:WorkspaceId
    userId = $bootstrap.me.id
    motionDocumentId = $motionDocument.documentId
    motionDocumentRevision = $motionDocument.revision
    motionDocumentVersion = $motionDocument.version
    motionPageId = "motion-distribuicao"
    motionGraphId = $motionGraph.graph.graphId
    motionGraphDigestSha256 = $motionGraph.graphDigestSha256
    motionRightsReviewId = $motionRights.review.reviewId
}
$motionStatePath = Join-Path $ArtifactRoot "distribuicao-motion-state.json"
$motionState | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $motionStatePath -Encoding utf8

[pscustomobject]@{
    workspaceId = $script:WorkspaceId
    sourceAssetId = $source.id
    musicAssetId = $music.id
    sourceIngestId = $sourceIngest.id
    musicIngestId = $musicIngest.id
    ugcDocumentId = $ugcDocument.documentId
    ugcDocumentRevision = $ugcDocument.revision
    ugcRightsReviewId = $ugcRights.review.reviewId
    ugcRenderJobId = $ugcJob.id
    ugcRenderAssetId = $ugcJob.result.artifact.assetId
    ugcOutput = $ugcOutput
    ugcQualityStatus = $ugcJob.result.qualityEvaluation.status
    ugcWarnings = $ugcJob.result.warnings
    motionDocumentId = $motionDocument.documentId
    motionGraphId = $motionGraph.graph.graphId
    motionGraphDigestSha256 = $motionGraph.graphDigestSha256
    motionStatePath = $motionStatePath
} | ConvertTo-Json -Depth 10
