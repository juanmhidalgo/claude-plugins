# API Design Patterns

## Contract-First Example

```typescript
// 1. Define the contract first
interface TaskAPI {
  createTask(input: CreateTaskInput): Promise<Task>;
  listTasks(params: ListTasksParams): Promise<PaginatedResult<Task>>;
  getTask(id: string): Promise<Task>;
  updateTask(id: string, input: UpdateTaskInput): Promise<Task>;
  deleteTask(id: string): Promise<void>;
}

// 2. Define input/output separation
interface CreateTaskInput {
  title: string;
  description?: string;
  priority?: 'low' | 'medium' | 'high';
}

interface Task {
  id: string;
  title: string;
  description: string | null;
  priority: 'low' | 'medium' | 'high';
  createdAt: Date;
  updatedAt: Date;
  createdBy: string;
}
```

## REST Resource Design

```
GET    /api/tasks              → List (with query params for filtering)
POST   /api/tasks              → Create
GET    /api/tasks/:id          → Get single
PATCH  /api/tasks/:id          → Partial update
DELETE /api/tasks/:id          → Delete

GET    /api/tasks/:id/comments → Sub-resource list
POST   /api/tasks/:id/comments → Sub-resource create
```

## Pagination

```typescript
// Request
GET /api/tasks?page=1&pageSize=20&sortBy=createdAt&sortOrder=desc

// Response
{
  "data": [...],
  "pagination": {
    "page": 1,
    "pageSize": 20,
    "totalItems": 142,
    "totalPages": 8
  }
}
```

## Boundary Validation

```typescript
import { z } from 'zod';

const CreateTaskSchema = z.object({
  title: z.string().min(1).max(200).trim(),
  description: z.string().max(2000).optional(),
  priority: z.enum(['low', 'medium', 'high']).default('medium'),
});

// Validate at the route handler — trust internal code after this
app.post('/api/tasks', async (req, res) => {
  const result = CreateTaskSchema.safeParse(req.body);
  if (!result.success) {
    return res.status(422).json({
      error: {
        code: 'VALIDATION_ERROR',
        message: 'Invalid task data',
        details: result.error.flatten(),
      },
    });
  }
  const task = await taskService.create(result.data);
  return res.status(201).json(task);
});
```

## Extending Without Breaking

```typescript
// GOOD: Add optional fields (backward compatible)
interface CreateTaskInput {
  title: string;
  description?: string;
  priority?: 'low' | 'medium' | 'high';  // Added later, optional
  labels?: string[];                       // Added later, optional
}

// BAD: Change existing field types or remove fields
// priority: number;  ← Changed from string — breaks consumers
// description removed ← breaks consumers
```

## Discriminated Unions for Variants

```typescript
type TaskStatus =
  | { type: 'pending' }
  | { type: 'in_progress'; assignee: string; startedAt: Date }
  | { type: 'completed'; completedAt: Date; completedBy: string }
  | { type: 'cancelled'; reason: string; cancelledAt: Date };
```

## Branded Types for IDs

```typescript
type TaskId = string & { readonly __brand: 'TaskId' };
type UserId = string & { readonly __brand: 'UserId' };

// Prevents accidentally passing a UserId where TaskId is expected
function getTask(id: TaskId): Promise<Task> { ... }
```

## Red Flags

- Endpoints returning different shapes depending on conditions
- Inconsistent error formats across endpoints
- Validation scattered throughout internal code
- Breaking changes to existing fields
- List endpoints without pagination
- Verbs in REST URLs (`/api/createTask`)
- Third-party API responses used without validation
