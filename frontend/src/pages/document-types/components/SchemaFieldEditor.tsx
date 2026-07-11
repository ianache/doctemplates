import { useState } from "react";
import { Control, UseFormRegister, useWatch } from "react-hook-form";
import { DocumentTypeFieldIn, FieldType } from "../../../lib/documentTypes";
import { SchemaFieldTreeNode, buildSchemaFieldTree } from "../../../lib/schemaFields";

interface SchemaFieldEditorProps {
  append: (value: DocumentTypeFieldIn) => void;
  remove: (index: number) => void;
  update: (index: number, value: DocumentTypeFieldIn) => void;
  register: UseFormRegister<any>;
  control: Control<any>;
}

export function SchemaFieldEditor({
  append,
  remove,
  update,
  register,
  control,
}: SchemaFieldEditorProps) {
  // Watch fields in real-time to build the hierarchical tree
  const watchedFields = useWatch({
    control,
    name: "fields",
    defaultValue: [],
  }) as DocumentTypeFieldIn[];

  const tree = buildSchemaFieldTree(watchedFields);

  // Set of collapsed node IDs (starts empty, so all nodes start expanded)
  const [collapsedNodes, setCollapsedNodes] = useState<Set<string>>(() => new Set());

  const toggleNode = (id: string) => {
    setCollapsedNodes((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  // Add field at the root level
  const handleAddRootField = () => {
    append({
      name: "new_field",
      type: "string",
      description: null,
    });
  };

  // Add field inside a parent object/list node
  const handleAddChild = (parentPath: string) => {
    append({
      name: `${parentPath}.new_field`,
      type: "string",
      description: null,
    });
  };

  // Rename path prefix for a parent node
  const renamePrefix = (fullPath: string, newSegment: string, isList: boolean) => {
    const parts = fullPath.split(".");
    const suffix = isList ? "[]" : "";
    parts[parts.length - 1] = newSegment + suffix;
    const newPath = parts.join(".");

    watchedFields.forEach((field, index) => {
      if (field.name === fullPath) {
        update(index, { ...field, name: newPath });
      } else if (field.name.startsWith(fullPath + ".")) {
        const remaining = field.name.slice(fullPath.length);
        update(index, { ...field, name: newPath + remaining });
      }
    });
  };

  // Rename a single leaf node's last path segment
  const handleSegmentChange = (index: number, currentName: string, newSegment: string) => {
    const segments = currentName.split(".");
    segments[segments.length - 1] = newSegment;
    const newName = segments.join(".");
    update(index, { ...watchedFields[index], name: newName });
  };

  // Handle changing type of a leaf node, with support for converting to object/list
  const handleTypeChange = (index: number, newType: FieldType | "object" | "list") => {
    const field = watchedFields[index];
    if (newType === "object") {
      // Append ".new_field" to make it an object parent
      update(index, { ...field, name: `${field.name}.new_field`, type: "string" });
    } else if (newType === "list") {
      // Append "[].new_field" to make it a list parent
      update(index, { ...field, name: `${field.name}[].new_field`, type: "string" });
    } else {
      // Simple type update
      update(index, { ...field, type: newType });
    }
  };

  // Recursively remove a parent node and all its children
  const removePrefix = (prefix: string) => {
    const indicesToRemove: number[] = [];
    watchedFields.forEach((field, index) => {
      if (field.name === prefix || field.name.startsWith(prefix + ".")) {
        indicesToRemove.push(index);
      }
    });
    // Sort descending to avoid index shifting problems during removal
    indicesToRemove.sort((a, b) => b - a);
    indicesToRemove.forEach((idx) => remove(idx));
  };

  const renderNode = (node: SchemaFieldTreeNode, depth: number) => {
    const isCollapsed = collapsedNodes.has(node.id);
    const isList = node.type === "list";
    const isObject = node.type === "object";
    const isLeaf = node.type === "leaf";

    return (
      <div key={node.id} className="mt-xs">
        <div className="flex items-center gap-sm py-xs hover:bg-surface-container-low/50 rounded px-xs group border border-transparent hover:border-outline-variant/30">
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

          {/* Segment Name Input */}
          {isLeaf ? (
            <input
              type="text"
              value={node.name}
              onChange={(e) => handleSegmentChange(node.fieldIndex!, node.fullPath, e.target.value)}
              className="rounded border border-outline px-sm py-xs font-mono text-sm text-on-surface focus:border-primary focus:outline-none w-[180px] bg-white"
              placeholder="field_name"
            />
          ) : (
            <input
              type="text"
              value={node.name}
              onChange={(e) => renamePrefix(node.fullPath, e.target.value, isList)}
              className="rounded border border-outline px-sm py-xs font-bold text-sm text-on-surface focus:border-primary focus:outline-none w-[180px] bg-white"
              placeholder="parent_name"
            />
          )}

          {/* Leaf Specific Type Selector and Description, or Parent Badge */}
          {isLeaf && node.fieldIndex !== undefined ? (
            <>
              {/* Type Select */}
              <select
                value={watchedFields[node.fieldIndex]?.type || "string"}
                onChange={(e) => handleTypeChange(node.fieldIndex!, e.target.value as any)}
                className="rounded border border-outline px-sm py-xs text-sm text-on-surface focus:border-primary focus:outline-none bg-white font-body-md"
              >
                <option value="string">String</option>
                <option value="number">Number</option>
                <option value="date">Date</option>
                <option value="boolean">Boolean</option>
                <option value="object">Object (nested)</option>
                <option value="list">List (nested list)</option>
              </select>

              {/* Description Input */}
              <input
                {...register(`fields.${node.fieldIndex}.description`)}
                placeholder="Description (optional)"
                className="rounded border border-outline px-sm py-xs text-sm text-on-surface focus:border-primary focus:outline-none flex-1 bg-white"
              />
            </>
          ) : (
            <>
              <span
                className={`text-[10px] font-bold px-1.5 py-0.5 rounded uppercase tracking-tighter ${
                  isList
                    ? "bg-surface-container-highest text-primary border border-outline-variant"
                    : "bg-secondary-container text-on-secondary-container"
                }`}
              >
                {isList ? "List" : "Object"}
              </span>
              <div className="flex-1"></div>
            </>
          )}

          {/* Action Buttons */}
          <div className="flex items-center gap-xs opacity-0 group-hover:opacity-100 transition-opacity">
            {!isLeaf && (
              <button
                type="button"
                onClick={() => handleAddChild(node.fullPath)}
                title="Add field inside"
                className="material-symbols-outlined text-secondary hover:text-primary transition-colors text-lg"
              >
                add_circle
              </button>
            )}
            <button
              type="button"
              onClick={() => (isLeaf ? remove(node.fieldIndex!) : removePrefix(node.fullPath))}
              title="Remove"
              className="material-symbols-outlined text-error hover:text-error/85 transition-colors text-lg"
            >
              delete
            </button>
          </div>
        </div>

        {/* Recursive Children Container */}
        {!isLeaf && !isCollapsed && (
          <div className="ml-lg border-l border-outline-variant/60 pl-sm space-y-xs">
            {node.children.map((child) => renderNode(child, depth + 1))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="border border-outline-variant rounded-lg p-md bg-surface-container-lowest">
      <div className="flex justify-between items-center border-b border-outline-variant pb-sm mb-sm bg-white p-xs">
        <h3 className="font-label-caps text-label-caps text-secondary uppercase">
          Document Fields Schema Builder
        </h3>
        <button
          type="button"
          onClick={handleAddRootField}
          className="flex items-center gap-xs bg-primary text-on-primary px-sm py-xs rounded hover:opacity-90 transition-opacity font-label-caps text-label-caps text-[11px]"
        >
          <span className="material-symbols-outlined text-sm">add</span> Add Root Field
        </button>
      </div>

      <div className="space-y-sm max-h-[500px] overflow-y-auto pr-xs">
        {tree.length === 0 ? (
          <div className="text-center py-lg border border-dashed border-outline-variant rounded bg-surface">
            <p className="text-sm text-secondary">No fields configured yet.</p>
            <button
              type="button"
              onClick={handleAddRootField}
              className="mt-xs text-sm font-bold text-primary hover:underline"
            >
              Add your first field
            </button>
          </div>
        ) : (
          tree.map((node) => renderNode(node, 0))
        )}
      </div>
    </div>
  );
}
