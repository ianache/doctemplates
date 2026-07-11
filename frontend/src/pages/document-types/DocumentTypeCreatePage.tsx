import { useEffect, useState } from "react";
import { useFieldArray, useForm } from "react-hook-form";
import { Link, useNavigate, useParams } from "react-router-dom";

import { createDocumentType, getDocumentType, updateDocumentType, type FieldType, type DocumentTypeMetadataIn } from "../../lib/documentTypes";
import { SchemaFieldEditor } from "./components/SchemaFieldEditor";
import { SchemaMetadataEditor } from "./components/SchemaMetadataEditor";
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

export default function DocumentTypeCreatePage() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const isEdit = !!id;
  
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [loading, setLoading] = useState(isEdit);
  
  const {
    register,
    control,
    handleSubmit,
    reset,
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

    // 1. Client-side validation for complex path constraints and structural conflicts
    const validationError = validateSchemaFields(values.fields);
    if (validationError) {
      setSubmitError(validationError);
      return;
    }

    // 2. Client-side normalization (trim names/descriptions)
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

      <form
        onSubmit={onSubmit}
        className="mt-xl rounded-lg border border-outline-variant bg-surface-container-lowest p-lg"
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
    </section>
  );
}
