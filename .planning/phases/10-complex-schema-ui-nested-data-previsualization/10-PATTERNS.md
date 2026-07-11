# Phase 10: Complex Schema UI & Nested Data Previsualization - Pattern Map

## File Classification
| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
| :--- | :--- | :--- | :--- | :--- |
| [schemaFields.ts](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/frontend/src/lib/schemaFields.ts) | utility | event-driven | [documentTypes.ts](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/frontend/src/lib/documentTypes.ts) | Good |
| [SchemaFieldEditor.tsx](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/frontend/src/pages/document-types/components/SchemaFieldEditor.tsx) | component | user input | [DocumentTypeCreatePage.tsx](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/frontend/src/pages/document-types/DocumentTypeCreatePage.tsx) | Good |
| [MockDataPanel.tsx](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/frontend/src/pages/document-designs/components/MockDataPanel.tsx) | component | user input | [DesignPageInspector.tsx](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/frontend/src/pages/document-designs/components/DesignPageInspector.tsx) | High |
| [PreviewFrame.tsx](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/frontend/src/pages/document-designs/components/PreviewFrame.tsx) | component | PDF I/O | [DocumentIssuanceDetailPage.tsx](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/frontend/src/pages/document-issuances/DocumentIssuanceDetailPage.tsx) | High |
| [documentDesigns.ts](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/frontend/src/lib/documentDesigns.ts) | service | request-response | [documentDesigns.ts](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/frontend/src/lib/documentDesigns.ts) | High |
| [DocumentTypeCreatePage.tsx](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/frontend/src/pages/document-types/DocumentTypeCreatePage.tsx) | page | user input | [DocumentTypeCreatePage.tsx](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/frontend/src/pages/document-types/DocumentTypeCreatePage.tsx) | High |
| [DocumentTypeDetailPage.tsx](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/frontend/src/pages/document-types/DocumentTypeDetailPage.tsx) | page | display | [DocumentTypeDetailPage.tsx](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/frontend/src/pages/document-types/DocumentTypeDetailPage.tsx) | High |
| [DocumentDesignDetailPage.tsx](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/frontend/src/pages/document-designs/DocumentDesignDetailPage.tsx) | page | composition | [DocumentDesignDetailPage.tsx](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/frontend/src/pages/document-designs/DocumentDesignDetailPage.tsx) | High |

## Pattern Assignments

### `schemaFields.ts` (utility, event-driven)
Analog: [documentTypes.ts](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/frontend/src/lib/documentTypes.ts)
* Excerpt for Type Declarations (Analogous to field types defined in [documentTypes.ts:L3-13](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/frontend/src/lib/documentTypes.ts#L3-13)):
```typescript
export type FieldType = "string" | "number" | "date" | "boolean";

export interface DocumentTypeFieldIn {
  name: string;
  type: FieldType;
  description: string | null;
}
```

* Excerpt for validation and tree adaptation rules (derived from python counterparts in [document_type.py:L20-109](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/backend/app/schemas/document_type.py#L20-109)):
```typescript
export interface SchemaFieldTreeNode {
  id: string; // unique ID for client-side keys
  name: string; // path segment name
  type: "leaf" | "object" | "list";
  fieldType?: FieldType; // populated only if type is "leaf"
  description: string | null;
  children: SchemaFieldTreeNode[];
}
```

### `SchemaFieldEditor.tsx` (component, user input)
Analog: [DocumentTypeCreatePage.tsx](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/frontend/src/pages/document-types/DocumentTypeCreatePage.tsx)
* Excerpt for form arrays and field actions (Analogous to [DocumentTypeCreatePage.tsx:L98-156](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/frontend/src/pages/document-types/DocumentTypeCreatePage.tsx#L98-156)):
```typescript
// Uses collapsible details/summary elements to represent object levels
// Exposes appending child nodes and removing nodes recursively
const renderNode = (node: SchemaFieldTreeNode, depth: number) => {
  return (
    <div key={node.id} style={{ marginLeft: `${depth * 16}px` }} className="border-l border-outline-variant pl-sm mt-xs">
      <div className="flex items-center gap-sm">
        <input 
          value={node.name}
          onChange={(e) => updateNodeName(node.id, e.target.value)}
          placeholder="field_name"
          className="rounded border border-outline px-sm py-xs text-sm"
        />
        <select
          value={node.type === "leaf" ? node.fieldType : node.type}
          onChange={(e) => updateNodeType(node.id, e.target.value)}
          className="rounded border border-outline px-sm py-xs text-sm"
        >
          <option value="string">String</option>
          <option value="number">Number</option>
          <option value="date">Date</option>
          <option value="boolean">Boolean</option>
          <option value="object">Object</option>
          <option value="list">List</option>
        </select>
        <button type="button" onClick={() => removeNode(node.id)} className="text-error font-bold">Remove</button>
      </div>
      {/* Recursively render child items if node is not a leaf */}
    </div>
  );
};
```

### `MockDataPanel.tsx` (component, user input)
Analog: [DesignPageInspector.tsx](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/frontend/src/pages/document-designs/components/DesignPageInspector.tsx)
* Excerpt for handling raw text JSON changes and validating with `SyntaxError` (Analogous to [DesignPageInspector.tsx:L39-54](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/frontend/src/pages/document-designs/components/DesignPageInspector.tsx#L39-54)):
```typescript
  const [configJson, setConfigJson] = useState("{}");
  const [error, setError] = useState<string | null>(null);

  const handleSave = async () => {
    setError(null);
    try {
      const parsed = JSON.parse(configJson) as Record<string, unknown>;
      onSave(parsed);
    } catch (err) {
      setError(err instanceof SyntaxError ? "Config must be valid JSON." : "We couldn't save this page.");
    }
  };
```

### `PreviewFrame.tsx` (component, PDF I/O)
Analog: [DocumentIssuanceDetailPage.tsx](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/frontend/src/pages/document-issuances/DocumentIssuanceDetailPage.tsx)
* Excerpt for iframe rendering, object URL lifecycle management, and cleanup (Analogous to [DocumentIssuanceDetailPage.tsx:L76-101](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/frontend/src/pages/document-issuances/DocumentIssuanceDetailPage.tsx#L76-101)):
```typescript
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    let objectUrl: string | null = null;
    setBlobUrl(null);
    setPreviewError(null);

    previewDocumentDesign(designId, mockPayload)
      .then((blob) => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        setBlobUrl(objectUrl);
      })
      .catch((err) => {
        if (!cancelled) {
          setPreviewError(err instanceof Error ? err.message : "Failed to load PDF preview.");
        }
      });

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [designId, mockPayload]);
```

### `documentDesigns.ts` (service, request-response)
Analog: [documentDesigns.ts:L66-82](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/frontend/src/lib/documentDesigns.ts#L66-82)
* Excerpt for API calls with JSON requests returning non-JSON responses (Blob):
```typescript
export async function previewDocumentDesign(
  designId: string,
  payload: Record<string, unknown>,
): Promise<Blob> {
  const res = await apiFetch(`/api/document-designs/${designId}/preview`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(readErrorMessage(body, res.status));
  }
  return res.blob();
}
```

### `DocumentTypeCreatePage.tsx` (page, user input)
Analog: [DocumentTypeCreatePage.tsx](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/frontend/src/pages/document-types/DocumentTypeCreatePage.tsx)
* Excerpt for validating payload before submission and handling submit (Analogous to [DocumentTypeCreatePage.tsx:L38-60](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/frontend/src/pages/document-types/DocumentTypeCreatePage.tsx#L38-60)):
```typescript
  const onSubmit = handleSubmit(async (values) => {
    setSubmitError(null);
    
    // Case-insensitive uniqueness check and structural validation
    const validationError = validateSchemaFields(values.fields);
    if (validationError) {
      setSubmitError(validationError);
      return;
    }

    try {
      const created = await createDocumentType({
        name: values.name,
        description: values.description || null,
        fields: values.fields,
      });
      navigate(`/document-types/${created.id}`);
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "We couldn't save this document type.");
    }
  });
```

### `DocumentTypeDetailPage.tsx` (page, display)
Analog: [DocumentTypeDetailPage.tsx:L62-79](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/frontend/src/pages/document-types/DocumentTypeDetailPage.tsx#L62-79)
* Excerpt for rendering tree hierarchy:
```typescript
  // Convert fields to tree first: const tree = parseFlatFieldsToTree(documentType.fields);
  // Recursively render node items with folder/collapsible icons as described in .design reference
```

### `DocumentDesignDetailPage.tsx` (page, composition)
Analog: [DocumentDesignDetailPage.tsx](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/frontend/src/pages/document-designs/DocumentDesignDetailPage.tsx)
* Excerpt for rendering togglable views, and persistence of mock payload in local storage:
```typescript
  const [previewMode, setPreviewMode] = useState<"page" | "pdf">("page");
  const [mockPayload, setMockPayload] = useState<Record<string, unknown>>(() => {
    const saved = localStorage.getItem(`mock_payload_${id}`);
    if (saved) {
      try { return JSON.parse(saved); } catch {}
    }
    // Fallback: generate default mock data structure from design's document type fields
    return generateMockPayloadFromFields(design.fields);
  });

  const handleMockPayloadChange = (nextPayload: Record<string, unknown>) => {
    setMockPayload(nextPayload);
    localStorage.setItem(`mock_payload_${id}`, JSON.stringify(nextPayload));
  };
```

## Shared Patterns
1. **Blob URL Lifecycle Management**: Always invoke `URL.createObjectURL` inside `useEffect` and return a cleanup function that revokes it with `URL.revokeObjectURL(objectUrl)` to prevent browser memory leaks.
2. **Case-Insensitive Input Validation**: Ensure duplicate checks lowercase all string values (`.toLowerCase().trim()`) to align with the backend's database constraints.
3. **Syntax Error Interception**: Prevent UI crashes on malformed JSON payload editing by validating input strings inside `try-catch` blocks and catching `SyntaxError`.

## No Analog Found
* **Recursive flat-to-tree schema parser**: No client-side code exists for converting path notation list payloads back and forth to nested objects. The implementation should implement a pure TypeScript module using string path parsing (`split('.')`) and segment parsing (detecting `[]` at the end of a segment for list types).

## Metadata
* **Confidence level:** HIGH
* **Date:** 2026-07-10
* **Applicability:** Precision Archival frontend and backend preview endpoint integrations.
