import { useWatch } from "react-hook-form";
import type { DocumentTypeMetadataIn } from "../../../lib/documentTypes";

interface SchemaMetadataEditorProps {
  append: (value: any) => void;
  remove: (index: number) => void;
  register: any;
  control: any;
}

export function SchemaMetadataEditor({
  append,
  remove,
  register,
  control,
}: SchemaMetadataEditorProps) {
  const watchedMetadata = useWatch({
    control,
    name: "metadata_definitions",
    defaultValue: [],
  }) as DocumentTypeMetadataIn[];

  const handleAddMetadata = () => {
    append({
      name: "new_metadata",
      type: "text",
      required: true,
    });
  };

  return (
    <div className="border border-outline-variant rounded-lg p-md bg-surface-container-lowest mt-lg">
      <div className="flex justify-between items-center border-b border-outline-variant pb-sm mb-sm bg-white p-xs">
        <h3 className="font-label-caps text-label-caps text-secondary uppercase">
          Document Metadata Schema Builder
        </h3>
        <button
          type="button"
          onClick={handleAddMetadata}
          className="flex items-center gap-xs bg-primary text-on-primary px-sm py-xs rounded hover:opacity-90 transition-opacity font-label-caps text-label-caps text-[11px]"
        >
          <span className="material-symbols-outlined text-sm">add</span> Add Metadata Field
        </button>
      </div>

      <div className="space-y-sm max-h-[300px] overflow-y-auto pr-xs">
        {watchedMetadata.length === 0 ? (
          <div className="text-center py-lg border border-dashed border-outline-variant rounded bg-surface">
            <p className="text-sm text-secondary">No metadata fields configured yet (optional).</p>
            <button
              type="button"
              onClick={handleAddMetadata}
              className="mt-xs text-sm font-bold text-primary hover:underline"
            >
              Add a metadata field
            </button>
          </div>
        ) : (
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-outline-variant text-[11px] font-bold text-secondary uppercase tracking-[0.05em]">
                <th className="pb-xs w-[250px]">Metadata Name</th>
                <th className="pb-xs w-[180px]">Data Type</th>
                <th className="pb-xs w-[120px]">Mandatory</th>
                <th className="pb-xs text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {watchedMetadata.map((_, index) => (
                <tr key={index} className="border-b border-outline-variant/40 hover:bg-surface-container-low/50">
                  <td className="py-sm pr-md">
                    <input
                      {...register(`metadata_definitions.${index}.name`, {
                        required: "Name is required",
                        pattern: {
                          value: /^[a-zA-Z_][a-zA-Z0-9_]*$/,
                          message: "Must be a valid alphanumeric identifier (no spaces/dots)"
                        }
                      })}
                      className="w-full rounded border border-outline px-sm py-xs font-mono text-sm text-on-surface focus:border-primary focus:outline-none bg-white"
                      placeholder="e.g. department_id"
                    />
                  </td>
                  <td className="py-sm pr-md">
                    <select
                      {...register(`metadata_definitions.${index}.type`)}
                      className="w-full rounded border border-outline px-sm py-xs text-sm text-on-surface focus:border-primary focus:outline-none bg-white"
                    >
                      <option value="text">Text</option>
                      <option value="number">Number</option>
                      <option value="date">Date (YYYY-MM-DD)</option>
                      <option value="datetime">Datetime (ISO 8601)</option>
                      <option value="boolean">Boolean</option>
                    </select>
                  </td>
                  <td className="py-sm pr-md">
                    <label className="flex items-center gap-xs cursor-pointer">
                      <input
                        type="checkbox"
                        {...register(`metadata_definitions.${index}.required`)}
                        className="rounded border-outline text-primary focus:ring-primary w-4 h-4"
                      />
                      <span className="text-body-sm">Required</span>
                    </label>
                  </td>
                  <td className="py-sm text-right">
                    <button
                      type="button"
                      onClick={() => remove(index)}
                      title="Remove"
                      className="material-symbols-outlined text-error hover:text-error/85 transition-colors text-lg"
                    >
                      delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
