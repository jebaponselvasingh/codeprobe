import { useState, useEffect } from 'react';
import { useProfileStore } from '../../stores/profileStore';

interface RubricCategory {
  name: string;
  weight: number;
  min_expectations: string;
}

const inputStyle: React.CSSProperties = {
  background: 'var(--bg-secondary)',
  border: '1px solid var(--border)',
  borderRadius: 8,
  padding: '8px 12px',
  color: 'var(--text-primary)',
  fontSize: 14,
  outline: 'none',
};

export function RubricEditorModal() {
  const { editingRubric, setEditingRubric, createRubric, updateRubric } = useProfileStore();

  const [name, setName] = useState(editingRubric?.name ?? '');
  const [categories, setCategories] = useState<RubricCategory[]>(
    (editingRubric?.categories ?? []) as RubricCategory[]
  );

  useEffect(() => {
    setName(editingRubric?.name ?? '');
    setCategories((editingRubric?.categories ?? []) as RubricCategory[]);
  }, [editingRubric]);

  if (!editingRubric) return null;

  const totalWeight = categories.reduce((s, c) => s + c.weight, 0);
  const weightsValid = Math.abs(totalWeight - 1.0) <= 0.01;
  const isValid = name.trim().length > 0 && categories.length > 0 && weightsValid;

  const addCategory = () => {
    setCategories(prev => [...prev, { name: '', weight: 0, min_expectations: '' }]);
  };

  const removeCategory = (i: number) => {
    setCategories(prev => prev.filter((_, idx) => idx !== i));
  };

  const updateCategory = (i: number, patch: Partial<RubricCategory>) => {
    setCategories(prev => prev.map((c, idx) => idx === i ? { ...c, ...patch } : c));
  };

  const handleSave = async () => {
    if (!isValid) return;
    const payload = { name, categories };
    if (editingRubric.id) {
      await updateRubric(editingRubric.id, payload);
    } else {
      await createRubric(payload);
    }
    setEditingRubric(null);
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ background: 'rgba(0,0,0,0.6)' }}
      onClick={e => { if (e.target === e.currentTarget) setEditingRubric(null); }}
    >
      <div
        className="w-full max-w-2xl flex flex-col gap-4 rounded-xl p-6"
        style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', maxHeight: '90vh', overflowY: 'auto' }}
      >
        <h2 className="text-lg font-semibold" style={{ color: 'var(--text-primary)' }}>
          {editingRubric.id ? 'Edit Rubric' : 'New Rubric'}
        </h2>

        <input
          placeholder="Rubric name"
          value={name}
          onChange={e => setName(e.target.value)}
          style={{ ...inputStyle, width: '100%' }}
        />

        {/* Category rows */}
        <div className="flex flex-col gap-2">
          {categories.map((cat, i) => (
            <div key={i} className="flex items-center gap-3">
              <input
                placeholder="Category name"
                value={cat.name}
                onChange={e => updateCategory(i, { name: e.target.value })}
                style={{ ...inputStyle, flex: 1 }}
              />
              <input
                type="number"
                min="0"
                max="100"
                placeholder="Weight %"
                value={Math.round(cat.weight * 100)}
                onChange={e => updateCategory(i, { weight: Number(e.target.value) / 100 })}
                style={{ ...inputStyle, width: 80 }}
              />
              <input
                placeholder="Min expectations..."
                value={cat.min_expectations}
                onChange={e => updateCategory(i, { min_expectations: e.target.value })}
                style={{ ...inputStyle, flex: 1 }}
              />
              <button
                onClick={() => removeCategory(i)}
                className="flex-shrink-0 w-7 h-7 rounded flex items-center justify-center text-sm hover:opacity-70"
                style={{ color: 'var(--text-muted)', background: 'var(--bg-secondary)', border: '1px solid var(--border)' }}
              >
                ✕
              </button>
            </div>
          ))}
        </div>

        {/* Weight validation */}
        <div className="text-sm flex items-center gap-2" style={{ color: 'var(--text-secondary)' }}>
          <span>Total: {Math.round(totalWeight * 100)}%</span>
          {categories.length > 0 && !weightsValid && (
            <span style={{ color: '#f87171' }}>Must sum to 100%</span>
          )}
          {categories.length > 0 && weightsValid && (
            <span style={{ color: 'var(--accent-green)' }}>Valid</span>
          )}
        </div>

        <button
          onClick={addCategory}
          className="text-sm py-2 rounded-lg"
          style={{
            border: '1px dashed var(--border)',
            color: 'var(--text-secondary)',
            background: 'transparent',
            cursor: 'pointer',
          }}
        >
          + Add Category
        </button>

        <div className="flex gap-2 justify-end">
          <button
            onClick={() => setEditingRubric(null)}
            className="px-4 py-2 rounded-lg text-sm"
            style={{
              background: 'var(--bg-secondary)',
              border: '1px solid var(--border)',
              color: 'var(--text-secondary)',
              cursor: 'pointer',
            }}
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={!isValid}
            className="px-4 py-2 rounded-lg text-sm font-medium"
            style={{
              background: isValid ? 'var(--accent-blue)' : 'var(--bg-secondary)',
              color: isValid ? '#fff' : 'var(--text-muted)',
              cursor: isValid ? 'pointer' : 'not-allowed',
              border: '1px solid transparent',
            }}
          >
            Save Rubric
          </button>
        </div>
      </div>
    </div>
  );
}
