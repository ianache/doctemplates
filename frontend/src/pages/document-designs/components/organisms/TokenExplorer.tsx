import { useMemo, useState } from "react";
import { buildSchemaFieldTree, type SchemaFieldTreeNode } from "../../../../lib/schemaFields";
import type { DocumentTypeFieldIn } from "../../../../lib/documentTypes";

interface TokenExplorerProps {
  fields: DocumentTypeFieldIn[];
  emptyMessage?: string;
  draggable?: boolean;
  className?: string;
  onTokenDragStart?: (node: SchemaFieldTreeNode, fields: DocumentTypeFieldIn[]) => string;
}

function getDefaultDragTextForNode(node: SchemaFieldTreeNode, fields: DocumentTypeFieldIn[]): string {
  if (node.type === "list") {
    const listPath = node.fullPath;
    const cleanPath = listPath.replace(/\[\]/g, "");
    const listVar = cleanPath.split(".").pop() || "item";
    const itemAlias = listVar.slice(0, -1) || "item";

    const childFields = fields.filter((field) => field.name.startsWith(cleanPath + "."));
    const columns = childFields.map((field) => {
      const relPath = field.name.slice((cleanPath + ".").length);
      return {
        header: relPath.split(".").pop() || relPath,
        expr: `{{ ${itemAlias}.${relPath} }}`,
      };
    });

    if (columns.length === 0) {
      columns.push({ header: "Item", expr: `{{ ${itemAlias} }}` });
    }

    return `
<table>
  <thead>
    <tr>
      ${columns.map((column) => `<th>${column.header}</th>`).join("\n      ")}
    </tr>
  </thead>
  <tbody>

    {% for ${itemAlias} in ${cleanPath} %}

    <tr>
      ${columns.map((column) => `<td>${column.expr}</td>`).join("\n      ")}
    </tr>

    {% endfor %}

  </tbody>
</table>`;
  }

  const isInsideList = node.fullPath.includes("[]");
  if (isInsideList) {
    const parts = node.fullPath.split("[]");
    const listPart = parts[0];
    const subPart = parts[1];
    const listVar = listPart.split(".").pop() || "item";
    const itemAlias = listVar.slice(0, -1) || "item";
    const cleanSubPart = subPart.startsWith(".") ? subPart.slice(1) : subPart;

    return `{% for ${itemAlias} in ${listPart} %}{{ ${itemAlias}.${cleanSubPart} }}{% endfor %}`;
  }

  return `{{ ${node.fullPath} }}`;
}

export default function TokenExplorer({
  fields,
  emptyMessage = "No tokens available.",
  draggable = false,
  className = "",
  onTokenDragStart = getDefaultDragTextForNode,
}: TokenExplorerProps) {
  const [collapsedNodes, setCollapsedNodes] = useState<Set<string>>(new Set());

  const tokenTree = useMemo(() => buildSchemaFieldTree(fields), [fields]);

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

  const renderNode = (node: SchemaFieldTreeNode) => {
    const isLeaf = node.type === "leaf";
    const isCollapsed = collapsedNodes.has(node.id);

    return (
      <div key={node.id} className="select-none mt-xs">
        <div
          draggable={draggable}
          onDragStart={(event) => {
            if (!draggable) return;
            event.dataTransfer.setData("text/plain", onTokenDragStart(node, fields));
          }}
          className={`flex items-center gap-xs py-xs px-sm rounded transition-colors group border border-transparent ${
            draggable
              ? "cursor-grab hover:bg-surface-container-high active:border-primary/30"
              : "cursor-default hover:bg-surface-container-low"
          } ${isLeaf ? "text-on-surface" : "font-bold text-secondary"}`}
        >
          {!isLeaf ? (
            <button
              type="button"
              onClick={(event) => {
                event.stopPropagation();
                toggleNode(node.id);
              }}
              className="material-symbols-outlined text-secondary hover:text-primary transition-colors text-[18px] focus:outline-none"
              aria-label={isCollapsed ? `Expand ${node.name}` : `Collapse ${node.name}`}
            >
              {isCollapsed ? "chevron_right" : "expand_more"}
            </button>
          ) : (
            <div className="w-[18px]" />
          )}

          <span className="material-symbols-outlined text-[18px] text-outline">
            {node.type === "list" ? "list" : node.type === "object" ? (isCollapsed ? "folder" : "folder_open") : "description"}
          </span>
          <span className="text-body-sm font-semibold truncate" title={node.fullPath}>
            {node.name}
          </span>
          {isLeaf && node.fieldType ? (
            <span className="ml-auto rounded bg-surface-container px-1.5 py-0.5 text-[10px] font-mono text-secondary">
              {node.fieldType}
            </span>
          ) : null}
        </div>

        {!isLeaf && !isCollapsed && node.children && (
          <div className="pl-md border-l border-outline-variant ml-sm space-y-xs">
            {node.children.map(renderNode)}
          </div>
        )}
      </div>
    );
  };

  if (tokenTree.length === 0) {
    return (
      <div className={`text-center py-lg border border-dashed border-outline-variant rounded bg-surface p-sm ${className}`}>
        <p className="text-xs text-secondary">{emptyMessage}</p>
      </div>
    );
  }

  return <div className={`space-y-xs pr-xs ${className}`}>{tokenTree.map(renderNode)}</div>;
}
