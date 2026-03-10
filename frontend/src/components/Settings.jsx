import React, { useState, useEffect } from 'react';
import { fetchEquipmentConfig, updateEquipmentConfig } from '../api/client';
import { Settings2, Loader2, Save } from 'lucide-react';

export default function Settings({ showToast }) {
    const [exercises, setExercises] = useState([]);
    const [loading, setLoading] = useState(true);
    const [savingId, setSavingId] = useState(null);

    // Local state for the input values, keyed by exercise_id
    const [inputs, setInputs] = useState({});

    useEffect(() => {
        loadConfig();
    }, []);

    async function loadConfig() {
        setLoading(true);
        try {
            const data = await fetchEquipmentConfig();
            setExercises(data);
            const initialInputs = {};
            data.forEach(ex => {
                initialInputs[ex.exercise_id] = ex.custom_increments?.join(', ') || '';
            });
            setInputs(initialInputs);
        } catch (err) {
            showToast('Failed to load equipment config', true);
        } finally {
            setLoading(false);
        }
    }

    const handleInputChange = (exerciseId, val) => {
        setInputs(prev => ({ ...prev, [exerciseId]: val }));
    };

    const handleSave = async (exerciseId) => {
        setSavingId(exerciseId);
        try {
            const rawStr = inputs[exerciseId] || '';
            // Parse string "7, 14, 21.5" into [7.0, 14.0, 21.5]
            const floatArr = rawStr
                .split(',')
                .map(s => s.trim())
                .filter(s => s !== '')
                .map(s => parseFloat(s))
                .filter(n => !isNaN(n));

            floatArr.sort((a, b) => a - b);

            await updateEquipmentConfig(exerciseId, floatArr);

            // Update local input state with correctly formatted string to show success visually
            setInputs(prev => ({ ...prev, [exerciseId]: floatArr.join(', ') }));

            showToast('Config saved!');
        } catch (err) {
            showToast(err.response?.data?.detail || err.message, true);
        } finally {
            setSavingId(null);
        }
    };

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center p-12 text-zinc-500 gap-3">
                <Loader2 className="animate-spin" size={24} />
                <p className="text-sm font-semibold uppercase tracking-widest">Loading Settings...</p>
            </div>
        );
    }

    return (
        <div className="max-w-xl mx-auto p-4 space-y-6">
            <div className="flex items-center gap-2 mb-6 text-zinc-300">
                <Settings2 size={24} className="text-sky-400" />
                <h2 className="text-xl font-bold uppercase tracking-widest">Machine Plate Configurations</h2>
            </div>

            <p className="text-sm text-zinc-500 mb-6">
                Configure the exact weight plates available for each machine. Enter comma-separated values (e.g. <span className="text-zinc-300 font-mono">7, 14, 21, 27.5, 35</span>). Leave empty to use generic 5kg jumps.
            </p>

            <div className="space-y-4">
                {exercises.map((ex) => (
                    <div key={ex.exercise_id} className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 flex flex-col gap-3">
                        <div className="flex items-center justify-between">
                            <h3 className="text-sm font-semibold text-zinc-200">{ex.name}</h3>
                            <span className="text-[10px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-400">
                                {ex.equipment}
                            </span>
                        </div>

                        <div className="flex gap-2">
                            <input
                                type="text"
                                placeholder="Ex: 7, 14, 21, 27.5"
                                className="flex-1 bg-black border border-zinc-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-sky-500 font-mono"
                                value={inputs[ex.exercise_id]}
                                onChange={(e) => handleInputChange(ex.exercise_id, e.target.value)}
                            />
                            <button
                                onClick={() => handleSave(ex.exercise_id)}
                                disabled={savingId === ex.exercise_id}
                                className="bg-zinc-800 text-sky-400 font-bold uppercase tracking-wider text-xs px-4 py-2 rounded-lg flex items-center justify-center min-w-[80px] hover:bg-zinc-700 active:bg-sky-400 active:text-black transition-colors disabled:opacity-50"
                            >
                                {savingId === ex.exercise_id ? (
                                    <Loader2 size={16} className="animate-spin" />
                                ) : (
                                    <>
                                        <Save size={14} className="mr-1.5" />
                                        Save
                                    </>
                                )}
                            </button>
                        </div>
                    </div>
                ))}
                {exercises.length === 0 && (
                    <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-8 text-center">
                        <p className="text-sm text-zinc-500">No machine exercises found in the catalog.</p>
                    </div>
                )}
            </div>
        </div>
    );
}
