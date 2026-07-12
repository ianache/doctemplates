import { useEffect, useState, useMemo } from "react";
import { useFieldArray, useForm } from "react-hook-form";
import { Link, useNavigate, useParams } from "react-router-dom";

import { createDocumentType, getDocumentType, updateDocumentType, type FieldType, type DocumentTypeMetadataIn } from "../../lib/documentTypes";
import { SchemaFieldEditor } from "./components/organisms/SchemaFieldEditor";
import { SchemaMetadataEditor } from "./components/organisms/SchemaMetadataEditor";
import { validateSchemaFields, normalizeSchemaFields } from "../../lib/schemaFields";

type FieldRow = {
  name: string;
  type: FieldType;
  description: string | null;
};

type FormValues = {
  name: string;
  description: string;
  fields: FieldRow[];
  metadata_definitions: DocumentTypeMetadataIn[];
};

function generateMockPayload(fields: FieldRow[], metadata: DocumentTypeMetadataIn[]) {
  const data: Record<string, any> = {};
  fields.forEach(f => {
    if (!f.name) return;
    const parts = f.name.split(".");
    let current = data;
    parts.forEach((part, index) => {
      const isList = part.endsWith("[]");
      const cleanName = isList ? part.slice(0, -2) : part;
      
      if (index === parts.length - 1) {
        if (isList) {
          current[cleanName] = [f.type === "number" ? 123 : f.type === "boolean" ? true : f.type === "date" ? "2026-07-11" : "Sample"];
        } else {
          current[cleanName] = f.type === "number" ? 123 : f.type === "boolean" ? true : f.type === "date" ? "2026-07-11" : "Sample";
        }
      } else {
        if (isList) {
          if (!current[cleanName]) current[cleanName] = [{}];
          current = current[cleanName][0];
        } else {
          if (!current[cleanName]) current[cleanName] = {};
          current = current[cleanName];
        }
      }
    });
  });

  const meta: Record<string, any> = {};
  metadata.forEach(m => {
    if (!m.name) return;
    meta[m.name] = m.type === "number" ? 123.45 : m.type === "boolean" ? true : m.type === "date" ? "2026-07-11" : m.type === "datetime" ? "2026-07-11T20:00:00Z" : "Sample Text";
  });

  return { data, metadata: meta };
}

function getCurlCode(typeId: string, payload: any, firstMetaName: string): string {
  return `# 1. Generar Documento
curl -X POST "http://localhost:8000/api/document-designs/YOUR_DESIGN_ID/generate" \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \\
  -d '${JSON.stringify(payload, null, 2)}'

# 2. Buscar por Metadatos
curl -X GET "http://localhost:8000/api/issuances?document_type_id=${typeId}${firstMetaName ? `&metadata.${firstMetaName}=Sample` : ""}" \\
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"`;
}

function getJSCode(typeId: string, payload: any, firstMetaName: string): string {
  return `// 1. Generar Documento
const generateDoc = async () => {
  const res = await fetch("http://localhost:8000/api/document-designs/YOUR_DESIGN_ID/generate", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": "Bearer YOUR_ACCESS_TOKEN"
    },
    body: JSON.stringify(${JSON.stringify(payload, null, 2).replace(/\n/g, "\n      ")})
  });
  const data = await res.json();
  console.log(data);
};

// 2. Buscar por Metadatos
const searchDocs = async () => {
  const url = "http://localhost:8000/api/issuances?document_type_id=${typeId}${firstMetaName ? `&metadata.${firstMetaName}=Sample` : ""}";
  const res = await fetch(url, {
    headers: {
      "Authorization": "Bearer YOUR_ACCESS_TOKEN"
    }
  });
  const list = await res.json();
  console.log(list);
};`;
}

function getPythonCode(typeId: string, payload: any, firstMetaName: string): string {
  return `import requests

# 1. Generar Documento
url = "http://localhost:8000/api/document-designs/YOUR_DESIGN_ID/generate"
headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer YOUR_ACCESS_TOKEN"
}
payload = ${JSON.stringify(payload, null, 4)}

response = requests.post(url, json=payload, headers=headers)
print("Creado:", response.json())

# 2. Buscar por Metadatos
search_url = "http://localhost:8000/api/issuances"
params = {
    "document_type_id": "${typeId}"${firstMetaName ? `,
    "metadata.${firstMetaName}": "Sample"` : ""}
}
response = requests.get(search_url, params=params, headers=headers)
print("Documentos:", response.json())`;
}

function getJavaCode(typeId: string, payload: any, firstMetaName: string): string {
  return `import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;

public class DocGen {
    public static void main(String[] args) throws Exception {
        HttpClient client = HttpClient.newHttpClient();

        // 1. Generar Documento
        String payload = """
${JSON.stringify(payload, null, 4)}
        """;

        HttpRequest reqGen = HttpRequest.newBuilder()
            .uri(URI.create("http://localhost:8000/api/document-designs/YOUR_DESIGN_ID/generate"))
            .header("Content-Type", "application/json")
            .header("Authorization", "Bearer YOUR_ACCESS_TOKEN")
            .POST(HttpRequest.BodyPublishers.ofString(payload))
            .build();

        HttpResponse<String> resGen = client.send(reqGen, HttpResponse.BodyHandlers.ofString());
        System.out.println("Generado: " + resGen.body());

        // 2. Buscar por Metadatos
        String queryUrl = "http://localhost:8000/api/issuances?document_type_id=${typeId}${firstMetaName ? `&metadata.${firstMetaName}=Sample` : ""}";
        HttpRequest reqQuery = HttpRequest.newBuilder()
            .uri(URI.create(queryUrl))
            .header("Authorization", "Bearer YOUR_ACCESS_TOKEN")
            .GET()
            .build();

        HttpResponse<String> resQuery = client.send(reqQuery, HttpResponse.BodyHandlers.ofString());
        System.out.println("Busqueda: " + resQuery.body());
    }
}`;
}

export default function DocumentTypeCreatePage() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const isEdit = !!id;
  
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [loading, setLoading] = useState(isEdit);
  const [activeLang, setActiveLang] = useState<"curl" | "js" | "py" | "java">("curl");
  
  const {
    register,
    control,
    handleSubmit,
    reset,
    watch,
    formState: { errors },
  } = useForm<FormValues>({
    defaultValues: {
      name: "",
      description: "",
      fields: [{ name: "new_field", type: "string", description: "" }],
      metadata_definitions: [],
    },
  });

  const { append, remove, update } = useFieldArray({ control, name: "fields" });
  const { append: appendMeta, remove: removeMeta } = useFieldArray({ control, name: "metadata_definitions" });

  // Watch fields and metadata definitions dynamically
  const watchedFields = watch("fields") || [];
  const watchedMetadata = watch("metadata_definitions") || [];

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    getDocumentType(id)
      .then((data) => {
        if (data) {
          reset({
            name: data.name,
            description: data.description || "",
            fields: data.fields.map((f) => ({
              name: f.name,
              type: f.type,
              description: f.description || "",
            })),
            metadata_definitions: data.metadata_definitions.map((m) => ({
              name: m.name,
              type: m.type,
              required: m.required,
            })),
          });
        }
      })
      .catch((err) => {
        setSubmitError(err instanceof Error ? err.message : "Failed to load document type.");
      })
      .finally(() => {
        setLoading(false);
      });
  }, [id, reset]);

  const onSubmit = handleSubmit(async (values) => {
    setSubmitError(null);

    const validationError = validateSchemaFields(values.fields);
    if (validationError) {
      setSubmitError(validationError);
      return;
    }

    const normalizedFields = normalizeSchemaFields(values.fields);

    try {
      const payload = {
        name: values.name,
        description: values.description || null,
        fields: normalizedFields,
        metadata_definitions: values.metadata_definitions,
      };
      const saved = isEdit
        ? await updateDocumentType(id!, payload)
        : await createDocumentType(payload);
      navigate(`/document-types/${saved.id}`);
    } catch (err) {
      setSubmitError(
        err instanceof Error
          ? err.message
          : "We couldn't save this document type. Check the fields below and try again."
      );
    }
  });

  // Calculate dynamic mock payload and snippets
  const mockPayload = useMemo(() => {
    return generateMockPayload(watchedFields, watchedMetadata);
  }, [watchedFields, watchedMetadata]);

  const firstMetaName = useMemo(() => {
    return watchedMetadata[0]?.name || "";
  }, [watchedMetadata]);

  const snippetCode = useMemo(() => {
    const typeId = id || "YOUR_DOCUMENT_TYPE_ID";
    if (activeLang === "curl") return getCurlCode(typeId, mockPayload, firstMetaName);
    if (activeLang === "js") return getJSCode(typeId, mockPayload, firstMetaName);
    if (activeLang === "py") return getPythonCode(typeId, mockPayload, firstMetaName);
    return getJavaCode(typeId, mockPayload, firstMetaName);
  }, [activeLang, id, mockPayload, firstMetaName]);

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <span className="material-symbols-outlined animate-spin text-secondary">progress_activity</span>
      </div>
    );
  }

  return (
    <section>
      <div className="flex items-center justify-between">
        <h1 className="font-headings text-[24px] font-bold leading-[32px] tracking-[-0.01em] text-on-surface">
          {isEdit ? "Edit Document Type" : "New Document Type"}
        </h1>
        {isEdit && (
          <Link
            to={`/document-types/${id}`}
            className="text-sm font-bold text-primary hover:underline flex items-center gap-xs"
          >
            <span className="material-symbols-outlined text-sm">arrow_back</span> Cancel
          </Link>
        )}
      </div>

      <div className={isEdit ? "grid grid-cols-[1fr_400px] gap-lg items-start mt-xl" : "mt-xl"}>
        {/* Left Column: Form */}
        <form
          onSubmit={onSubmit}
          className="rounded-lg border border-outline-variant bg-surface-container-lowest p-lg shadow-sm"
        >
          {submitError ? (
            <div className="mb-md rounded border border-error/30 bg-background p-sm text-sm text-error">
              {submitError}
            </div>
          ) : null}

          <div className="space-y-md mb-lg">
            <label className="block text-[11px] font-bold uppercase leading-[16px] tracking-[0.05em] text-secondary">
              Name
              <input
                {...register("name", { required: "Name is required." })}
                className="mt-xs w-full rounded border border-outline px-sm py-xs text-sm text-on-surface focus:border-primary focus:outline-none bg-white"
                placeholder="e.g. Invoice, Contract"
              />
            </label>
            {errors.name ? <p className="text-sm text-error">{errors.name.message}</p> : null}

            <label className="block text-[11px] font-bold uppercase leading-[16px] tracking-[0.05em] text-secondary">
              Description
              <textarea
                {...register("description")}
                rows={3}
                className="mt-xs w-full rounded border border-outline px-sm py-xs text-sm text-on-surface focus:border-primary focus:outline-none bg-white"
                placeholder="Describe the purpose of this document type..."
              />
            </label>
          </div>

          {/* Visual Schema Tree Builder */}
          <div className="mt-lg">
            <SchemaFieldEditor
              register={register}
              control={control}
              append={append}
              remove={remove}
              update={update}
            />
          </div>

          {/* Visual Metadata Builder */}
          <SchemaMetadataEditor
            register={register}
            control={control}
            append={appendMeta}
            remove={removeMeta}
          />

          <div className="mt-lg flex justify-end">
            <button
              type="submit"
              className="rounded bg-primary px-lg py-sm text-sm font-bold text-white hover:bg-primary/90"
            >
              {isEdit ? "Save Changes" : "Create Document Type"}
            </button>
          </div>
        </form>

        {/* Right Column: API Integration Panel (Only visible on Edit screen) */}
        {isEdit && (
          <aside className="rounded-lg border border-outline-variant bg-surface-container-lowest p-md sticky top-4 max-h-[750px] overflow-y-auto flex flex-col gap-sm shadow-sm select-none">
            <div className="border-b border-outline-variant pb-xs">
              <h3 className="font-headings text-[14px] font-bold text-on-surface flex items-center gap-xs">
                <span className="material-symbols-outlined text-primary text-[20px]">api</span>
                INTEGRATION CODE EXAMPLES
              </h3>
              <p className="text-[11px] text-secondary mt-xs leading-relaxed">
                Connect your codebase to generate and query documents using this schema.
              </p>
            </div>

            {/* Language Selection Badges / Tabs */}
            <div className="flex flex-wrap gap-xs border border-outline-variant p-0.5 rounded-md bg-surface-container-low select-none">
              {(["curl", "js", "py", "java"] as const).map((lang) => (
                <button
                  key={lang}
                  type="button"
                  onClick={() => setActiveLang(lang)}
                  className={`flex-1 text-center py-1 rounded text-xs font-bold transition-all ${
                    activeLang === lang
                      ? "bg-white text-primary shadow-sm"
                      : "text-secondary hover:text-on-surface"
                  }`}
                >
                  {lang === "curl" ? "cURL" : lang === "js" ? "JS" : lang === "py" ? "Python" : "Java"}
                </button>
              ))}
            </div>

            {/* Code Workspace */}
            <div className="flex-1 min-h-0 relative">
              <pre className="w-full bg-slate-900 text-slate-100 p-sm rounded-lg font-mono text-[11px] leading-relaxed overflow-x-auto select-all max-h-[480px]">
                <code>{snippetCode}</code>
              </pre>
            </div>

            {/* Info badge */}
            <div className="rounded bg-surface-container p-xs border border-outline-variant text-[10px] leading-relaxed text-secondary">
              <div className="font-bold text-on-surface mb-0.5 flex items-center gap-1">
                <span className="material-symbols-outlined text-[12px] text-primary">key</span>
                Cookie Session Authentication
              </div>
              These endpoints require cookie authentication. Supply the session cookie <code className="bg-white px-0.5 border rounded font-mono">docmanagement_session</code> in your request headers.
            </div>
          </aside>
        )}
      </div>
    </section>
  );
}
