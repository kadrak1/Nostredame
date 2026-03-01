import { useState, useRef, useCallback, useEffect, useMemo } from 'react';
import { Stage, Layer, Rect, Circle, Line, Text, Group, Transformer } from 'react-konva';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Konva from 'konva';
import api from '../../api/client';

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

type TableShape = 'rect' | 'circle';

interface TableData {
  id?: number;
  number: number;
  capacity: number;
  x: number;
  y: number;
  width: number;
  height: number;
  shape: TableShape;
  is_active?: boolean;
}

interface WallData {
  id: string;
  points: number[]; // [x1,y1,x2,y2]
  strokeWidth: number;
}

interface FloorPlanData {
  width: number;
  height: number;
  walls: WallData[];
}

interface FloorPlanResponse {
  floor_plan: FloorPlanData | null;
  tables: TableData[];
}

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const GRID_SIZE = 20;
const CANVAS_W = 1200;
const CANVAS_H = 800;
const MIN_TABLE_SIZE = 40;
const DEFAULT_TABLE: Omit<TableData, 'number'> = {
  capacity: 4,
  x: 100,
  y: 100,
  width: 80,
  height: 80,
  shape: 'rect',
};

const COLORS = {
  grid: '#1a2a4a',
  table: '#2ECC71',
  tableStroke: '#27AE60',
  tableSelected: '#E94560',
  tableSelectedStroke: '#d63b54',
  wall: '#8892A0',
  wallPreview: '#E94560',
  text: '#FFFFFF',
  canvasBg: '#0F1923',
};

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function snapToGrid(val: number): number {
  return Math.round(val / GRID_SIZE) * GRID_SIZE;
}

function clamp(val: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, val));
}

function generateWallId(): string {
  return 'w_' + Date.now() + '_' + Math.random().toString(36).slice(2, 7);
}

/* ------------------------------------------------------------------ */
/*  Grid component                                                     */
/* ------------------------------------------------------------------ */

function GridLines({ width, height }: { width: number; height: number }) {
  const lines: React.ReactNode[] = [];
  for (let x = 0; x <= width; x += GRID_SIZE) {
    lines.push(
      <Line key={`v${x}`} points={[x, 0, x, height]} stroke={COLORS.grid} strokeWidth={0.5} />
    );
  }
  for (let y = 0; y <= height; y += GRID_SIZE) {
    lines.push(
      <Line key={`h${y}`} points={[0, y, width, y]} stroke={COLORS.grid} strokeWidth={0.5} />
    );
  }
  return <>{lines}</>;
}

/* ------------------------------------------------------------------ */
/*  Table shape component                                              */
/* ------------------------------------------------------------------ */

interface TableNodeProps {
  table: TableData;
  isSelected: boolean;
  onSelect: () => void;
  onChange: (attrs: Partial<TableData>) => void;
}

function TableNode({ table, isSelected, onSelect, onChange }: TableNodeProps) {
  const shapeRef = useRef<Konva.Rect | Konva.Circle>(null);
  const trRef = useRef<Konva.Transformer>(null);

  useEffect(() => {
    if (isSelected && trRef.current && shapeRef.current) {
      trRef.current.nodes([shapeRef.current]);
      trRef.current.getLayer()?.batchDraw();
    }
  }, [isSelected]);

  const handleDragEnd = (e: Konva.KonvaEventObject<DragEvent>) => {
    const node = e.target;
    onChange({
      x: snapToGrid(clamp(node.x(), 0, CANVAS_W - table.width)),
      y: snapToGrid(clamp(node.y(), 0, CANVAS_H - table.height)),
    });
  };

  const handleTransformEnd = () => {
    const node = shapeRef.current;
    if (!node) return;
    const scaleX = node.scaleX();
    const scaleY = node.scaleY();
    node.scaleX(1);
    node.scaleY(1);

    const newWidth = Math.max(MIN_TABLE_SIZE, snapToGrid(node.width() * scaleX));
    const newHeight = Math.max(MIN_TABLE_SIZE, snapToGrid(node.height() * scaleY));

    onChange({
      x: snapToGrid(node.x()),
      y: snapToGrid(node.y()),
      width: newWidth,
      height: newHeight,
    });
  };

  const fill = isSelected ? COLORS.tableSelected : COLORS.table;
  const stroke = isSelected ? COLORS.tableSelectedStroke : COLORS.tableStroke;

  return (
    <Group>
      {table.shape === 'circle' ? (
        <Circle
          ref={shapeRef as React.RefObject<Konva.Circle>}
          x={table.x + table.width / 2}
          y={table.y + table.height / 2}
          radius={table.width / 2}
          width={table.width}
          height={table.height}
          fill={fill}
          stroke={stroke}
          strokeWidth={2}
          draggable
          onClick={onSelect}
          onTap={onSelect}
          onDragEnd={(e) => {
            const node = e.target;
            onChange({
              x: snapToGrid(clamp(node.x() - table.width / 2, 0, CANVAS_W - table.width)),
              y: snapToGrid(clamp(node.y() - table.height / 2, 0, CANVAS_H - table.height)),
            });
          }}
          onTransformEnd={handleTransformEnd}
        />
      ) : (
        <Rect
          ref={shapeRef as React.RefObject<Konva.Rect>}
          x={table.x}
          y={table.y}
          width={table.width}
          height={table.height}
          fill={fill}
          stroke={stroke}
          strokeWidth={2}
          cornerRadius={6}
          draggable
          onClick={onSelect}
          onTap={onSelect}
          onDragEnd={handleDragEnd}
          onTransformEnd={handleTransformEnd}
        />
      )}
      {/* Table number label */}
      <Text
        x={table.x}
        y={table.y + table.height / 2 - 14}
        width={table.width}
        align="center"
        text={`#${table.number}`}
        fontSize={14}
        fontStyle="bold"
        fill={COLORS.text}
        listening={false}
      />
      {/* Capacity label */}
      <Text
        x={table.x}
        y={table.y + table.height / 2 + 2}
        width={table.width}
        align="center"
        text={`${table.capacity} чел.`}
        fontSize={11}
        fill="rgba(255,255,255,0.7)"
        listening={false}
      />
      {isSelected && (
        <Transformer
          ref={trRef}
          rotateEnabled={false}
          enabledAnchors={['top-left', 'top-right', 'bottom-left', 'bottom-right']}
          boundBoxFunc={(_oldBox, newBox) => {
            if (newBox.width < MIN_TABLE_SIZE || newBox.height < MIN_TABLE_SIZE) {
              return _oldBox;
            }
            return newBox;
          }}
        />
      )}
    </Group>
  );
}

/* ------------------------------------------------------------------ */
/*  Main FloorPlan component                                           */
/* ------------------------------------------------------------------ */

type Tool = 'select' | 'wall';

export default function FloorPlan() {
  const queryClient = useQueryClient();
  const stageRef = useRef<Konva.Stage>(null);

  // --- State ---
  const [tables, setTables] = useState<TableData[]>([]);
  const [walls, setWalls] = useState<WallData[]>([]);
  const [selectedTableIdx, setSelectedTableIdx] = useState<number | null>(null);
  const [activeTool, setActiveTool] = useState<Tool>('select');
  const [drawingWall, setDrawingWall] = useState<number[] | null>(null);
  const [hasChanges, setHasChanges] = useState(false);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');

  // --- Edit popup state ---
  const [editNumber, setEditNumber] = useState('');
  const [editCapacity, setEditCapacity] = useState('');
  const [editShape, setEditShape] = useState<TableShape>('rect');

  // --- Data fetching ---
  const [initialized, setInitialized] = useState(false);
  const { data: floorData, isLoading, isError } = useQuery({
    queryKey: ['floor-plan'],
    queryFn: () => api.get<FloorPlanResponse>('/venue/floor-plan').then((r) => r.data),
    refetchOnWindowFocus: false,
  });

  // Initialize local state from server data (once, during render — official React pattern)
  if (floorData && !initialized) {
    setInitialized(true);
    setTables(floorData.tables ?? []);
    const fp = floorData.floor_plan;
    if (fp && fp.walls) {
      setWalls(fp.walls);
    }
  }

  // --- Table CRUD mutations ---
  const createTableMut = useMutation({
    mutationFn: (t: TableData) => api.post<TableData>('/tables', t).then((r) => r.data),
  });

  const updateTableMut = useMutation({
    mutationFn: ({ id, ...data }: TableData & { id: number }) =>
      api.put<TableData>(`/tables/${id}`, data).then((r) => r.data),
  });

  const deleteTableMut = useMutation({
    mutationFn: (id: number) => api.delete(`/tables/${id}`),
  });

  // --- Floor plan save ---
  const saveFloorPlanMut = useMutation({
    mutationFn: (floorPlan: FloorPlanData) =>
      api.put<FloorPlanResponse>('/venue/floor-plan', { floor_plan: floorPlan }).then((r) => r.data),
  });

  // --- Select table helper (sync edit fields immediately) ---
  const selectTable = useCallback(
    (idx: number | null) => {
      setSelectedTableIdx(idx);
      if (idx !== null && tables[idx]) {
        const t = tables[idx];
        setEditNumber(String(t.number));
        setEditCapacity(String(t.capacity));
        setEditShape(t.shape);
      }
    },
    [tables]
  );

  // Derive selected table for render
  const selectedTable = useMemo(
    () => (selectedTableIdx !== null ? tables[selectedTableIdx] : null),
    [selectedTableIdx, tables]
  );

  // --- Handlers ---

  const markChanged = useCallback(() => {
    setHasChanges(true);
    setSaveStatus('idle');
  }, []);

  const handleTableChange = useCallback(
    (idx: number, attrs: Partial<TableData>) => {
      setTables((prev) => {
        const next = [...prev];
        next[idx] = { ...next[idx], ...attrs };
        return next;
      });
      markChanged();
    },
    [markChanged]
  );

  const addTable = useCallback(
    (shape: TableShape) => {
      const maxNum = tables.reduce((m, t) => Math.max(m, t.number), 0);
      const newTable: TableData = {
        ...DEFAULT_TABLE,
        shape,
        number: maxNum + 1,
        x: snapToGrid(100 + Math.random() * 200),
        y: snapToGrid(100 + Math.random() * 200),
      };
      setTables((prev) => [...prev, newTable]);
      selectTable(tables.length);
      markChanged();
    },
    [tables, markChanged, selectTable]
  );

  const deleteSelectedTable = useCallback(() => {
    if (selectedTableIdx === null) return;
    setTables((prev) => prev.filter((_, i) => i !== selectedTableIdx));
    selectTable(null);
    markChanged();
  }, [selectedTableIdx, markChanged, selectTable]);

  const applyEditFields = useCallback(() => {
    if (selectedTableIdx === null) return;
    const num = parseInt(editNumber);
    const cap = parseInt(editCapacity);
    if (isNaN(num) || num < 1 || isNaN(cap) || cap < 1 || cap > 50) return;

    // Check unique number
    const duplicate = tables.some((t, i) => i !== selectedTableIdx && t.number === num);
    if (duplicate) return;

    handleTableChange(selectedTableIdx, { number: num, capacity: cap, shape: editShape });
  }, [selectedTableIdx, editNumber, editCapacity, editShape, tables, handleTableChange]);

  // --- Wall drawing ---
  const handleStageMouseDown = useCallback(
    (e: Konva.KonvaEventObject<MouseEvent>) => {
      if (activeTool !== 'wall') return;
      const stage = e.target.getStage();
      if (!stage) return;
      const pos = stage.getPointerPosition();
      if (!pos) return;
      setDrawingWall([snapToGrid(pos.x), snapToGrid(pos.y), snapToGrid(pos.x), snapToGrid(pos.y)]);
    },
    [activeTool]
  );

  const handleStageMouseMove = useCallback(
    (e: Konva.KonvaEventObject<MouseEvent>) => {
      if (!drawingWall) return;
      const stage = e.target.getStage();
      if (!stage) return;
      const pos = stage.getPointerPosition();
      if (!pos) return;
      setDrawingWall([drawingWall[0], drawingWall[1], snapToGrid(pos.x), snapToGrid(pos.y)]);
    },
    [drawingWall]
  );

  const handleStageMouseUp = useCallback(() => {
    if (!drawingWall) return;
    const [x1, y1, x2, y2] = drawingWall;
    // Only add if wall has length
    if (Math.abs(x2 - x1) > GRID_SIZE || Math.abs(y2 - y1) > GRID_SIZE) {
      setWalls((prev) => [
        ...prev,
        { id: generateWallId(), points: [x1, y1, x2, y2], strokeWidth: 6 },
      ]);
      markChanged();
    }
    setDrawingWall(null);
  }, [drawingWall, markChanged]);

  const deleteWall = useCallback(
    (wallId: string) => {
      setWalls((prev) => prev.filter((w) => w.id !== wallId));
      markChanged();
    },
    [markChanged]
  );

  // --- Deselect on click on empty area ---
  const handleStageClick = useCallback(
    (e: Konva.KonvaEventObject<MouseEvent>) => {
      if (activeTool === 'wall') return;
      if (e.target === e.target.getStage()) {
        selectTable(null);
      }
    },
    [activeTool, selectTable]
  );

  // --- Save all ---
  const handleSave = useCallback(async () => {
    setSaveStatus('saving');
    try {
      // 1. Save floor plan (walls/decorations)
      const floorPlan: FloorPlanData = {
        width: CANVAS_W,
        height: CANVAS_H,
        walls,
      };
      await saveFloorPlanMut.mutateAsync(floorPlan);

      // 2. Sync tables: create new, update existing, delete removed
      const serverTables = floorData?.tables ?? [];
      const serverIds = new Set(serverTables.map((t) => t.id));
      const currentIds = new Set(tables.filter((t) => t.id).map((t) => t.id));

      // Delete tables that were removed
      for (const st of serverTables) {
        if (st.id && !currentIds.has(st.id)) {
          await deleteTableMut.mutateAsync(st.id);
        }
      }

      // Create or update tables
      const updatedTables: TableData[] = [];
      for (const t of tables) {
        if (t.id && serverIds.has(t.id)) {
          // Update
          const result = await updateTableMut.mutateAsync({
            id: t.id,
            number: t.number,
            capacity: t.capacity,
            x: t.x,
            y: t.y,
            width: t.width,
            height: t.height,
            shape: t.shape,
          });
          updatedTables.push(result);
        } else {
          // Create
          const result = await createTableMut.mutateAsync({
            number: t.number,
            capacity: t.capacity,
            x: t.x,
            y: t.y,
            width: t.width,
            height: t.height,
            shape: t.shape,
          });
          updatedTables.push(result);
        }
      }

      setTables(updatedTables);
      setHasChanges(false);
      setSaveStatus('saved');
      queryClient.invalidateQueries({ queryKey: ['floor-plan'] });

      setTimeout(() => setSaveStatus('idle'), 2000);
    } catch {
      setSaveStatus('error');
    }
  }, [walls, tables, floorData, saveFloorPlanMut, createTableMut, updateTableMut, deleteTableMut, queryClient]);

  // --- Discard changes ---
  const handleDiscard = useCallback(() => {
    if (floorData) {
      setTables(floorData.tables ?? []);
      setWalls(floorData.floor_plan?.walls ?? []);
    } else {
      setTables([]);
      setWalls([]);
    }
    selectTable(null);
    setHasChanges(false);
    setSaveStatus('idle');
  }, [floorData, selectTable]);

  // --- Keyboard shortcuts ---
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Delete' || e.key === 'Backspace') {
        if (selectedTableIdx !== null && !(e.target instanceof HTMLInputElement)) {
          deleteSelectedTable();
        }
      }
      if (e.key === 'Escape') {
        selectTable(null);
        setActiveTool('select');
        setDrawingWall(null);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [selectedTableIdx, deleteSelectedTable, selectTable]);

  // --- Container responsiveness ---
  const containerRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(1);

  useEffect(() => {
    const updateScale = () => {
      if (containerRef.current) {
        const containerWidth = containerRef.current.offsetWidth;
        const newScale = Math.min(1, (containerWidth - 16) / CANVAS_W);
        setScale(newScale);
      }
    };
    updateScale();
    window.addEventListener('resize', updateScale);
    return () => window.removeEventListener('resize', updateScale);
  }, []);

  // --- Render ---
  if (isLoading) {
    return (
      <div className="admin-page">
        <h1>Конструктор зала</h1>
        <p className="info-muted">Загрузка...</p>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="admin-page">
        <h1>Конструктор зала</h1>
        <p className="error">Не удалось загрузить данные зала</p>
      </div>
    );
  }

  return (
    <div className="admin-page floor-plan-page">
      <div className="fp-header">
        <h1>Конструктор зала</h1>
        <div className="fp-header-actions">
          <button
            className="btn btn-primary"
            disabled={!hasChanges || saveStatus === 'saving'}
            onClick={handleSave}
          >
            {saveStatus === 'saving' ? 'Сохранение...' : 'Сохранить'}
          </button>
          <button
            className="btn fp-btn-secondary"
            disabled={!hasChanges}
            onClick={handleDiscard}
          >
            Отменить
          </button>
          {saveStatus === 'saved' && <span className="fp-save-ok">Сохранено!</span>}
          {saveStatus === 'error' && <span className="fp-save-err">Ошибка сохранения</span>}
        </div>
      </div>

      <div className="fp-workspace">
        {/* Toolbar */}
        <div className="fp-toolbar">
          <div className="fp-toolbar-section">
            <h3>Инструменты</h3>
            <button
              className={`fp-tool-btn ${activeTool === 'select' ? 'active' : ''}`}
              onClick={() => { setActiveTool('select'); setDrawingWall(null); }}
              title="Выделение / перемещение"
            >
              <span className="fp-tool-icon">&#9995;</span>
              Выделение
            </button>
            <button
              className={`fp-tool-btn ${activeTool === 'wall' ? 'active' : ''}`}
              onClick={() => { setActiveTool('wall'); selectTable(null); }}
              title="Рисование стен"
            >
              <span className="fp-tool-icon">&#9473;</span>
              Стена
            </button>
          </div>

          <div className="fp-toolbar-section">
            <h3>Добавить стол</h3>
            <button className="fp-tool-btn" onClick={() => addTable('rect')}>
              <span className="fp-tool-icon">&#9632;</span>
              Прямоуг.
            </button>
            <button className="fp-tool-btn" onClick={() => addTable('circle')}>
              <span className="fp-tool-icon">&#9679;</span>
              Круглый
            </button>
          </div>

          {/* Properties panel */}
          {selectedTable && (
            <div className="fp-toolbar-section fp-properties">
              <h3>Свойства стола</h3>
              <label>
                Номер
                <input
                  type="number"
                  min={1}
                  value={editNumber}
                  onChange={(e) => setEditNumber(e.target.value)}
                  onBlur={applyEditFields}
                />
              </label>
              <label>
                Вместимость
                <input
                  type="number"
                  min={1}
                  max={50}
                  value={editCapacity}
                  onChange={(e) => setEditCapacity(e.target.value)}
                  onBlur={applyEditFields}
                />
              </label>
              <label>
                Форма
                <select
                  value={editShape}
                  onChange={(e) => {
                    setEditShape(e.target.value as TableShape);
                    // Apply immediately
                    if (selectedTableIdx !== null) {
                      handleTableChange(selectedTableIdx, { shape: e.target.value as TableShape });
                    }
                  }}
                >
                  <option value="rect">Прямоугольник</option>
                  <option value="circle">Круг</option>
                </select>
              </label>
              <div className="fp-prop-info">
                <span>X: {selectedTable.x}</span>
                <span>Y: {selectedTable.y}</span>
                <span>{selectedTable.width}x{selectedTable.height}</span>
              </div>
              <button className="btn fp-btn-danger" onClick={deleteSelectedTable}>
                Удалить стол
              </button>
            </div>
          )}

          {/* Walls list */}
          {walls.length > 0 && (
            <div className="fp-toolbar-section">
              <h3>Стены ({walls.length})</h3>
              {walls.map((w) => (
                <div key={w.id} className="fp-wall-item">
                  <span className="info-muted">Стена</span>
                  <button
                    className="fp-wall-del"
                    onClick={() => deleteWall(w.id)}
                    title="Удалить стену"
                  >
                    &times;
                  </button>
                </div>
              ))}
            </div>
          )}

          <div className="fp-toolbar-section">
            <h3>Статистика</h3>
            <p className="info-muted">Столов: {tables.length}</p>
            <p className="info-muted">
              Мест: {tables.reduce((s, t) => s + t.capacity, 0)}
            </p>
          </div>
        </div>

        {/* Canvas */}
        <div className="fp-canvas-wrap" ref={containerRef}>
          <Stage
            ref={stageRef}
            width={CANVAS_W * scale}
            height={CANVAS_H * scale}
            scaleX={scale}
            scaleY={scale}
            style={{ background: COLORS.canvasBg, borderRadius: '8px' }}
            onClick={handleStageClick}
            onMouseDown={handleStageMouseDown}
            onMouseMove={handleStageMouseMove}
            onMouseUp={handleStageMouseUp}
          >
            {/* Grid layer */}
            <Layer listening={false}>
              <GridLines width={CANVAS_W} height={CANVAS_H} />
            </Layer>

            {/* Walls layer */}
            <Layer>
              {walls.map((w) => (
                <Line
                  key={w.id}
                  points={w.points}
                  stroke={COLORS.wall}
                  strokeWidth={w.strokeWidth}
                  lineCap="round"
                  hitStrokeWidth={12}
                  onClick={() => {
                    if (activeTool === 'select') {
                      // double-click to delete walls
                    }
                  }}
                  onDblClick={() => deleteWall(w.id)}
                  onDblTap={() => deleteWall(w.id)}
                />
              ))}
              {/* Wall preview while drawing */}
              {drawingWall && (
                <Line
                  points={drawingWall}
                  stroke={COLORS.wallPreview}
                  strokeWidth={6}
                  lineCap="round"
                  dash={[10, 5]}
                />
              )}
            </Layer>

            {/* Tables layer */}
            <Layer>
              {tables.map((table, idx) => (
                <TableNode
                  key={table.id ?? `new-${idx}`}
                  table={table}
                  isSelected={selectedTableIdx === idx}
                  onSelect={() => {
                    if (activeTool === 'select') {
                      selectTable(idx);
                    }
                  }}
                  onChange={(attrs) => handleTableChange(idx, attrs)}
                />
              ))}
            </Layer>
          </Stage>

          {activeTool === 'wall' && (
            <div className="fp-canvas-hint">
              Кликните и потяните для рисования стены. Esc — отмена.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
