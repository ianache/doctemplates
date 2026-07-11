import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { type DocumentTypeDetail, getDocumentType } from "../../lib/documentTypes";
import { buildSchemaFieldTree } from "../../lib/schemaFields";
import type { SchemaFieldTreeNode } from "../../lib/schemaFields";

export default function DocumentTypeDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [documentType, setDocumentType] = useState<DocumentTypeDetail | null | undefined>(
    undefined,
  );

  const [collapsedNodes, setCollapsedNodes] = useState<Set<string>>(() => new Set());

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    getDocumentType(id).then((data) => {
      if (!cancelled) setDocumentType(data);
    });
    return () => {
      cancelled = true;
    };
  }, [id]);

  if (documentType === undefined) return null;

  if (documentType === null) {
    return (
      <div className="text-center">
        <h1 className="font-headings text-[24px] font-bold leading-[32px] tracking-[-0.01em] text-on-surface">
          Document type not found.
        </h1>
        <p className="mt-sm text-sm leading-5 text-on-surface-variant">
          It may have been removed. Return to the list to see all document types.
        </p>
        <Link
          to="/document-types"
          className="mt-lg inline-block rounded bg-primary px-lg py-sm text-sm font-bold text-white hover:bg-primary/90"
        >
          Back to Document Types
        </Link>
      </div>
    );
  }

  const toggleNode = (nodeId: string) => {
    setCollapsedNodes((prev) => {
      const next = new Set(prev);
      if (next.has(nodeId)) {
        next.delete(nodeId);
      } else {
        next.add(nodeId);
      }
      return next;
    });
  };

  const renderNode = (node: SchemaFieldTreeNode, depth: number) => {
    const isCollapsed = collapsedNodes.has(node.id);
    const isList = node.type === "list";
    const isObject = node.type === "object";
    const isLeaf = node.type === "leaf";

    return (
      <div key={node.id} className="mt-xs">
        <div className="flex items-center gap-sm py-xs px-sm hover:bg-surface-container-low/50 rounded border border-transparent hover:border-outline-variant/30">
          {/* Collapse Toggle Chevron */}
          {!isLeaf ? (
            <button
              type="button"
              onClick={() => toggleNode(node.id)}
              className="material-symbols-outlined text-secondary hover:text-primary transition-colors text-lg focus:outline-none"
            >
              {isCollapsed ? "chevron_right" : "expand_more"}
            </button>
          ) : (
            <div className="w-[18px]"></div>
          )}

          {/* Type Icon */}
          <span className="material-symbols-outlined text-secondary text-lg">
            {isList ? "list" : isObject ? (isCollapsed ? "folder" : "folder_open") : "description"}
          </span>

          {/* Segment Name & Details */}
          {isLeaf ? (
            <div className="flex flex-wrap items-center gap-md flex-1 min-w-0">
              <span className="font-mono text-sm font-bold text-on-surface truncate">
                {node.name}
              </span>
              <code className="text-[11px] text-secondary font-mono bg-surface-container px-1.5 py-0.5 rounded truncate" title="Canonical Path">
                {node.fullPath}
              </code>
              <span className="rounded bg-surface-container-high px-2 py-0.5 text-[11px] font-bold uppercase text-on-surface-variant shrink-0 font-body-md">
                {node.fieldType}
              </span>
              {node.description && (
                <span className="text-sm text-on-surface-variant truncate" title={node.description}>
                  — {node.description}
                </span>
              )}
            </div>
          ) : (
            <div className="flex items-center gap-xs">
              <span className="font-bold text-sm text-on-surface">{node.name}</span>
              <span
                className={`text-[10px] font-bold px-1.5 py-0.5 rounded uppercase tracking-tighter ${
                  isList
                    ? "bg-surface-container-highest text-primary border border-outline-variant"
                    : "bg-secondary-container text-on-secondary-container"
                }`}
              >
                {isList ? "List" : "Object"}
              </span>
            </div>
          )}
        </div>

        {/* Recursive Child Nodes Container */}
        {!isLeaf && !isCollapsed && (
          <div className="ml-lg border-l border-outline-variant/60 pl-sm space-y-xs">
            {node.children.map((child) => renderNode(child, depth + 1))}
          </div>
        )}
      </div>
    );
  };

  const tree = buildSchemaFieldTree(documentType.fields);

  return (
    <section>
      <div className="flex items-center justify-between">
        <h1 className="font-headings text-[24px] font-bold leading-[32px] tracking-[-0.01em] text-on-surface">
          {documentType.name}
        </h1>
        <div className="flex items-center gap-md">
          <Link
            to={`/document-types/${documentType.id}/edit`}
            className="flex items-center gap-xs rounded border border-primary px-md py-xs text-sm font-bold text-primary hover:bg-primary/10 active:scale-95 transition-all"
          >
            <span className="material-symbols-outlined text-sm">edit</span> Edit
          </Link>
          <Link
            to="/document-types"
            className="text-sm font-bold text-primary hover:underline flex items-center gap-xs"
          >
            <span className="material-symbols-outlined text-sm">arrow_back</span> Back to List
          </Link>
        </div>
      </div>
      <p className="mt-xs text-sm leading-5 text-on-surface-variant">{documentType.description}</p>

      <div className="mt-md flex justify-between border-b border-outline-variant/30 pb-xs text-sm">
        <span className="text-on-surface-variant">Created By</span>
        <span className="text-on-surface">{documentType.created_by_email}</span>
      </div>
      <div className="flex justify-between border-b border-outline-variant/30 pb-xs pt-xs text-sm">
        <span className="text-on-surface-variant">Created At</span>
        <span className="text-on-surface">
          {new Date(documentType.created_at).toLocaleDateString()}
        </span>
      </div>

      {/* Collapsible Schema Tree Display */}
      <div className="mt-xl rounded-lg border border-outline-variant bg-surface-container-lowest p-md">
        <div className="border-b border-outline-variant pb-sm mb-sm bg-white p-xs">
          <h3 className="font-label-caps text-label-caps text-secondary uppercase">
            Document Fields Schema
          </h3>
        </div>

        <div className="space-y-xs">
          {tree.length === 0 ? (
            <p className="text-sm text-on-surface-variant py-md text-center">
              No fields defined for this document type.
            </p>
          ) : (
            tree.map((node) => renderNode(node, 0))
          )}
        </div>
      </div>

      {/* Collapsible Metadata Schema Display */}
      <div className="mt-xl rounded-lg border border-outline-variant bg-surface-container-lowest p-md">
        <div className="border-b border-outline-variant pb-sm mb-sm bg-white p-xs">
          <h3 className="font-label-caps text-label-caps text-secondary uppercase">
            Document Metadata Schema
          </h3>
        </div>

        <div className="space-y-xs">
          {!documentType.metadata_definitions || documentType.metadata_definitions.length === 0 ? (
            <p className="text-sm text-on-surface-variant py-md text-center">
              No metadata fields defined for this document type.
            </p>
          ) : (
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-outline-variant text-[11px] font-bold text-secondary uppercase tracking-[0.05em]">
                  <th className="pb-xs">Name</th>
                  <th className="pb-xs">Type</th>
                  <th className="pb-xs">Required</th>
                </tr>
              </thead>
              <tbody>
                {documentType.metadata_definitions.map((meta) => (
                  <tr key={meta.id} className="border-b border-outline-variant/40 hover:bg-surface-container-low/50">
                    <td className="py-sm font-mono text-sm text-on-surface font-semibold">{meta.name}</td>
                    <td className="py-sm">
                      <span className="rounded bg-surface-container-high px-2 py-0.5 text-[11px] font-bold uppercase text-on-surface-variant font-mono">
                        {meta.type}
                      </span>
                    </td>
                    <td className="py-sm text-body-sm text-on-surface-variant font-semibold">
                      {meta.required ? (
                        <span className="text-error">Yes</span>
                      ) : (
                        <span className="text-on-surface-variant opacity-60">No</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </section>
  );
}
