import { useState } from "react";
import { useFieldArray, useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";

import { createDocumentType, type FieldType } from "../../lib/documentTypes";
import { SchemaFieldEditor } from "./components/SchemaFieldEditor";
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
};

export default function DocumentTypeCreatePage() {
  const navigate = useNavigate();
  const [submitError, setSubmitError] = useState<string | null>(null);
  
  const {
    register,
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({
    defaultValues: {
      name: "",
      description: "",
      fields: [{ name: "new_field", type: "string", description: "" }],
    },
  });

  const { append, remove, update } = useFieldArray({ control, name: "fields" });

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
      const created = await createDocumentType({
        name: values.name,
        description: values.description || null,
        fields: normalizedFields,
      });
      navigate(`/document-types/${created.id}`);
    } catch (err) {
      setSubmitError(
        err instanceof Error
          ? err.message
          : "We couldn't save this document type. Check the fields below and try again."
      );
    }
  });

  return (
    <section>
      <h1 className="font-headings text-[24px] font-bold leading-[32px] tracking-[-0.01em] text-on-surface">
        New Document Type
      </h1>

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
              className="mt-xs w-full rounded border border-outline px-sm py-xs text-sm text-on-surface focus:border-primary focus:outline-none"
              placeholder="e.g. Invoice, Contract"
            />
          </label>
          {errors.name ? <p className="text-sm text-error">{errors.name.message}</p> : null}

          <label className="block text-[11px] font-bold uppercase leading-[16px] tracking-[0.05em] text-secondary">
            Description
            <textarea
              {...register("description")}
              rows={3}
              className="mt-xs w-full rounded border border-outline px-sm py-xs text-sm text-on-surface focus:border-primary focus:outline-none"
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

        <div className="mt-lg flex justify-end">
          <button
            type="submit"
            className="rounded bg-primary px-lg py-sm text-sm font-bold text-white hover:bg-primary/90"
          >
            Create Document Type
          </button>
        </div>
      </form>
    </section>
  );
}
