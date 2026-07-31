/* eslint-disable @typescript-eslint/no-explicit-any */
/* Generated from schemas/content/unit-document-v2.schema.json. Do not edit. */

export type Node = (ImageAsset | AudioAsset | VideoAsset | DownloadAsset | LegacyNode)
export type NodeId = string
export type AssetVersionId = string
export type PlainText = string

/**
 * Canonical semantic unit content with immutable academic asset references.
 */
export interface LMSUnitAcademicDocumentVersion2 {
type: "doc"
/**
 * @minItems 1
 * @maxItems 1000
 */
content: [Node, ...(Node)[]]
}
export interface ImageAsset {
type: "imageAsset"
attrs: {
[k: string]: any
}
}
export interface AudioAsset {
type: "audioAsset"
attrs: {
nodeId: NodeId
assetVersionId: AssetVersionId
title: string
transcript: string
caption: PlainText
}
}
export interface VideoAsset {
type: "videoAsset"
attrs: {
[k: string]: any
}
}
export interface DownloadAsset {
type: ("documentAsset" | "datasetAsset")
attrs: {
nodeId: NodeId
assetVersionId: AssetVersionId
label: string
description: PlainText
}
}
export interface LegacyNode {
type: string
attrs?: {
[k: string]: any
}
/**
 * @maxItems 5000
 */
content?: Node[]
text?: string
/**
 * @maxItems 4
 */
marks?: []|[{
[k: string]: any
}]|[{
[k: string]: any
}, {
[k: string]: any
}]|[{
[k: string]: any
}, {
[k: string]: any
}, {
[k: string]: any
}]|[{
[k: string]: any
}, {
[k: string]: any
}, {
[k: string]: any
}, {
[k: string]: any
}]
[k: string]: any
}
