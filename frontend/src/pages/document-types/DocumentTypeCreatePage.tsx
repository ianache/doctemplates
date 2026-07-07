import { useState } from "react";
import { useFieldArray, useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";

import { createDocumentType, type FieldType } from "../../lib/documentTypes";

type FieldRow = {
  name: string;
  type: FieldType;
  description: string;
};

type FormValues = {
  name: string;
  description: string;
  fields: FieldRow[];
};

const FIELD_TYPES: FieldType[] = ["string", "number", "date", "boolean"];

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
      fields: [{ name: "", type: "string", description: "" }],
    },
  });
  const { fields, append, remove } = useFieldArray({ control, name: "fields" });

  const onSubmit = handleSubmit(async (values) => {
    setSubmitError(null);
    const names = values.fields.map((field) => field.name);
    if (new Set(names).size !== names.length) {
      setSubmitError("Field names must be unique within a document type.");
      return;
    }

    try {
      const created = await createDocumentType({
        name: values.name,
        description: values.description || null,
        fields: values.fields.map((field) => ({
          name: field.name,
          type: field.type,
          description: field.description || null,
        })),
      });
      navigate(`/document-types/${created.id}`);
    } catch {
      setSubmitError("We couldn't save this document type. Check the fields below and try again.");
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
          <p className="mb-md rounded border border-error/30 bg-background p-sm text-sm text-error">
            {submitError}
          </p>
        ) : null}

        <div className="space-y-md">
          <label className="block text-[11px] font-bold uppercase leading-[16px] tracking-[0.05em] text-secondary">
            Name
            <input
              {...register("name", { required: "Name is required." })}
              className="mt-xs w-full rounded border border-outline px-sm py-xs text-sm text-on-surface focus:border-primary focus:outline-none"
            />
          </label>
          {errors.name ? <p className="text-sm text-error">{errors.name.message}</p> : null}

          <label className="block text-[11px] font-bold uppercase leading-[16px] tracking-[0.05em] text-secondary">
            Description
            <textarea
              {...register("description")}
              rows={3}
              className="mt-xs w-full rounded border border-outline px-sm py-xs text-sm text-on-surface focus:border-primary focus:outline-none"
            />
          </label>
        </div>

        <div className="mt-lg space-y-sm">
          {fields.map((field, index) => (
            <div key={field.id} className="flex items-end gap-sm border-t border-outline-variant pt-sm">
              <label className="flex-1 text-[11px] font-bold uppercase leading-[16px] tracking-[0.05em] text-secondary">
                Name
                <input
                  {...register(`fields.${index}.name`, { required: "Name is required." })}
                  className="mt-xs w-full rounded border border-outline px-sm py-xs font-mono text-sm text-on-surface focus:border-primary focus:outline-none"
                />
                {errors.fields?.[index]?.name ? (
                  <p className="mt-xs text-sm text-error">{errors.fields[index]?.name?.message}</p>
                ) : null}
              </label>

              <label className="text-[11px] font-bold uppercase leading-[16px] tracking-[0.05em] text-secondary">
                Type
                <select
                  {...register(`fields.${index}.type`, {
                    required: "Choose a field type.",
                  })}
                  className="mt-xs rounded border border-outline px-sm py-xs text-sm text-on-surface focus:border-primary focus:outline-none"
                >
                  {FIELD_TYPES.map((type) => (
                    <option key={type} value={type}>
                      {type}
                    </option>
                  ))}
                </select>
                {errors.fields?.[index]?.type ? (
                  <p className="mt-xs text-sm text-error">{errors.fields[index]?.type?.message}</p>
                ) : null}
              </label>

              <label className="flex-1 text-[11px] font-bold uppercase leading-[16px] tracking-[0.05em] text-secondary">
                Description
                <input
                  {...register(`fields.${index}.description`)}
                  className="mt-xs w-full rounded border border-outline px-sm py-xs text-sm text-on-surface focus:border-primary focus:outline-none"
                />
              </label>

              <button
                type="button"
                onClick={() => remove(index)}
                className="rounded border border-outline-variant px-sm py-xs text-sm font-bold text-on-surface hover:border-outline"
              >
                Remove
              </button>
            </div>
          ))}
        </div>

        <button
          type="button"
          onClick={() => append({ name: "", type: "string", description: "" })}
          className="mt-md rounded border border-primary px-md py-xs text-sm font-bold text-primary hover:bg-primary/10"
        >
          Add field
        </button>

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
