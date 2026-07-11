import type { FieldType, DocumentTypeFieldIn } from "./documentTypes";

export interface SchemaFieldTreeNode {
  id: string;
  name: string;
  type: "leaf" | "object" | "list";
  fieldType?: FieldType;
  description: string | null;
  children: SchemaFieldTreeNode[];
  fullPath: string;
  fieldIndex?: number;
}

/**
 * Builds a visual nested/list tree from flat path fields.
 * e.g., cliente.direccion.calle -> nested object nodes
 * e.g., cliente.contactos[].nombre -> nested list nodes
 */
export function buildSchemaFieldTree(fields: DocumentTypeFieldIn[]): SchemaFieldTreeNode[] {
  const root: SchemaFieldTreeNode[] = [];
  let idCounter = 1;

  for (let index = 0; index < fields.length; index++) {
    const field = fields[index];
    const trimmedName = field.name.trim();
    if (!trimmedName) continue;

    const segments = trimmedName.split(".");
    let currentLevel = root;
    let pathAccumulator = "";

    for (let i = 0; i < segments.length; i++) {
      const segment = segments[i];
      const isLast = i === segments.length - 1;
      const isList = segment.endsWith("[]");
      const cleanName = isList ? segment.slice(0, -2) : segment;

      if (pathAccumulator) {
        pathAccumulator += "." + segment;
      } else {
        pathAccumulator = segment;
      }

      // Find if segment already exists in currentLevel (case-insensitive check)
      let node = currentLevel.find(
        (n) => n.name.toLowerCase() === cleanName.toLowerCase()
      );

      if (!node) {
        node = {
          id: `node-${idCounter++}`,
          name: cleanName,
          type: isLast ? "leaf" : isList ? "list" : "object",
          fieldType: isLast ? field.type : undefined,
          description: isLast ? field.description : null,
          children: [],
          fullPath: pathAccumulator,
          fieldIndex: isLast ? index : undefined,
        };
        currentLevel.push(node);
      } else {
        // If node already exists, update properties if it's now a leaf
        if (isLast) {
          node.type = "leaf";
          node.fieldType = field.type;
          node.description = field.description;
          node.fieldIndex = index;
        } else if (node.type === "leaf") {
          // Re-classify leaf node as intermediate parent if subpaths are added
          node.type = isList ? "list" : "object";
          delete node.fieldType;
          delete node.fieldIndex;
          node.description = null;
        }
      }
      currentLevel = node.children;
    }
  }

  return root;
}

const PARENT_SEGMENT_RE = /^[a-zA-Z_][a-zA-Z0-9_]*(?:\[\])?$/;
const LEAF_SEGMENT_RE = /^[a-zA-Z_][a-zA-Z0-9_]*$/;

/**
 * Validates flat schema fields against backend constraints:
 * - Depth <= 5
 * - Valid segment names (alphanumeric/underscores)
 * - Intermediate segments can end in []
 * - Leaf segments must not end in []
 * - Case-insensitive uniqueness
 * - Structural conflicts
 */
export function validateSchemaFields(fields: DocumentTypeFieldIn[]): string | null {
  if (fields.length === 0) {
    return "At least one field is required";
  }

  const lowerNames = new Set<string>();

  for (const field of fields) {
    const name = field.name.trim();
    if (!name) {
      return "Field name cannot be empty";
    }

    const segments = name.split(".");
    if (segments.length > 5) {
      return `Field path depth cannot exceed 5 levels: "${name}"`;
    }

    for (let i = 0; i < segments.length; i++) {
      const segment = segments[i];
      if (!segment) {
        return `Field path segments cannot be empty in "${name}"`;
      }
      if (i < segments.length - 1) {
        if (!PARENT_SEGMENT_RE.test(segment)) {
          return `Invalid parent path segment: "${segment}" in "${name}"`;
        }
      } else {
        if (!LEAF_SEGMENT_RE.test(segment)) {
          return `Invalid leaf path segment: "${segment}" in "${name}". Leaf segments must not end in "[]"`;
        }
      }
    }

    const lowerName = name.toLowerCase();
    if (lowerNames.has(lowerName)) {
      return `Field names must be unique within a document type (case-insensitive duplicate: "${name}")`;
    }
    lowerNames.add(lowerName);
  }

  // Structural conflict verification
  type StructureNode =
    | { type: "leaf"; fieldType: FieldType }
    | { type: "object"; children: Record<string, StructureNode> }
    | { type: "list"; elementNode: { type: "object"; children: Record<string, StructureNode> } };

  const root: { type: "object"; children: Record<string, StructureNode> } = {
    type: "object",
    children: {},
  };

  for (const field of fields) {
    const segments = field.name.split(".");
    let current = root;

    for (let i = 0; i < segments.length; i++) {
      const segment = segments[i];
      const isLast = i === segments.length - 1;
      const isList = segment.endsWith("[]");
      const cleanName = (isList ? segment.slice(0, -2) : segment).toLowerCase();

      if (isLast) {
        if (current.children[cleanName]) {
          return `Conflict: "${field.name}" collides with an existing field path or parent`;
        }
        current.children[cleanName] = {
          type: "leaf",
          fieldType: field.type,
        };
      } else {
        if (current.children[cleanName]) {
          const existing = current.children[cleanName];
          if (existing.type === "leaf") {
            return `Conflict: "${field.name}" uses "${cleanName}" as a parent, which is already a leaf`;
          }
          if (isList) {
            if (existing.type !== "list") {
              return `Conflict: Path segment "${segment}" is declared as both a list and a non-list`;
            }
            current = existing.elementNode;
          } else {
            if (existing.type !== "object") {
              return `Conflict: Path segment "${segment}" is declared as both an object and a non-object/leaf`;
            }
            current = existing;
          }
        } else {
          if (isList) {
            const elementNode: { type: "object"; children: Record<string, StructureNode> } = {
              type: "object",
              children: {},
            };
            const newNode: StructureNode = {
              type: "list",
              elementNode,
            };
            current.children[cleanName] = newNode;
            current = elementNode;
          } else {
            const newNode: StructureNode = {
              type: "object",
              children: {},
            };
            current.children[cleanName] = newNode;
            current = newNode;
          }
        }
      }
    }
  }

  return null;
}

/**
 * Normalizes field names/descriptions by trimming whitespace
 * and ensuring database-compliant values.
 */
export function normalizeSchemaFields(fields: DocumentTypeFieldIn[]): DocumentTypeFieldIn[] {
  return fields.map((field) => ({
    name: field.name.trim(),
    type: field.type,
    description: field.description?.trim() || null,
  }));
}

function getSampleValue(type: FieldType): any {
  switch (type) {
    case "number":
      return 123.45;
    case "boolean":
      return true;
    case "date":
      return "2026-07-10";
    case "string":
    default:
      return "sample";
  }
}

/**
 * Generates a nested/array mock JSON object from flat schema fields.
 * e.g., cliente.direccion.calle -> { cliente: { direccion: { calle: "sample" } } }
 * e.g., cliente.contactos[].nombre -> { cliente: { contactos: [{ nombre: "sample" }] } }
 */
export function generateMockDataFromFields(fields: DocumentTypeFieldIn[]): Record<string, any> {
  const result: Record<string, any> = {};

  for (const field of fields) {
    const trimmedName = field.name.trim();
    if (!trimmedName) continue;

    const segments = trimmedName.split(".");
    let current: any = result;

    for (let i = 0; i < segments.length; i++) {
      const segment = segments[i];
      const isLast = i === segments.length - 1;
      const isList = segment.endsWith("[]");
      const cleanName = isList ? segment.slice(0, -2) : segment;

      if (isLast) {
        current[cleanName] = getSampleValue(field.type);
      } else {
        if (isList) {
          if (!current[cleanName]) {
            current[cleanName] = [];
          }
          if (current[cleanName].length === 0) {
            current[cleanName].push({});
          }
          current = current[cleanName][0];
        } else {
          if (!current[cleanName]) {
            current[cleanName] = {};
          }
          current = current[cleanName];
        }
      }
    }
  }

  return result;
}
