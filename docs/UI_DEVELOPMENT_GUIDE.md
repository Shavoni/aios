# AIOS UI Development Guide

**Version:** 1.0.0  
**Last Updated:** January 2026  
**Target Audience:** Developers looking to customize or extend the AIOS user interface

---

## Table of Contents

1. [What is AIOS?](#what-is-aios)
2. [UI Stack Overview](#ui-stack-overview)
3. [Architecture](#architecture)
4. [Getting Started](#getting-started)
5. [Component Library](#component-library)
6. [Customizing the UI](#customizing-the-ui)
7. [Creating New Pages](#creating-new-pages)
8. [Theming & Branding](#theming--branding)
9. [Best Practices](#best-practices)
10. [Examples](#examples)

---

## What is AIOS?

**AIOS (AI Operating System)** is an Enterprise AI Governance Platform for multi-agent orchestration. It is **NOT** a UI builder tool. Instead, AIOS provides:

- A **pre-built professional dashboard UI** for managing AI agents
- A **concierge chat interface** for end-users
- A **component library** based on shadcn/ui for building enterprise UIs
- An **extensible architecture** for customizing and adding new features

### Can AIOS Help You Build Professional UIs?

**Yes, but indirectly:**

✅ AIOS includes a complete, production-ready UI built with modern best practices  
✅ You can study, customize, and extend the existing UI components  
✅ The UI uses professional libraries (shadcn/ui, Radix UI, Tailwind CSS)  
✅ All components are TypeScript-typed and fully documented  

❌ AIOS is not a drag-and-drop UI builder or design tool  
❌ AIOS focuses on AI agent management, not general web development  

---

## UI Stack Overview

The AIOS frontend is built with modern, production-grade technologies:

### Core Technologies

| Technology | Version | Purpose |
|------------|---------|---------|
| **Next.js** | 16.1.4 | React framework with App Router |
| **React** | 19.2.3 | UI library |
| **TypeScript** | 5.x | Type safety |
| **Tailwind CSS** | 4.x | Utility-first styling |
| **shadcn/ui** | Latest | Component library |

### Key Libraries

| Library | Purpose |
|---------|---------|
| **@radix-ui** | Unstyled, accessible UI primitives |
| **lucide-react** | Icon library (600+ icons) |
| **next-themes** | Dark/light mode support |
| **sonner** | Toast notifications |
| **SWR** | Data fetching and caching |
| **class-variance-authority** | Type-safe component variants |

---

## Architecture

### Directory Structure

```
web/
├── src/
│   ├── app/                    # Next.js App Router pages
│   │   ├── (dashboard)/        # Dashboard layout group
│   │   │   ├── agents/         # Agent management page
│   │   │   ├── analytics/      # Analytics dashboard
│   │   │   ├── approvals/      # HITL approvals
│   │   │   ├── audit/          # Audit logs
│   │   │   ├── onboarding/     # Agent onboarding wizard
│   │   │   ├── runs/           # Execution history
│   │   │   ├── settings/       # System settings
│   │   │   ├── templates/      # Configuration templates
│   │   │   ├── tenants/        # Multi-tenant management
│   │   │   ├── page.tsx        # Dashboard home
│   │   │   └── layout.tsx      # Dashboard layout
│   │   ├── chat/               # Public chat interface
│   │   ├── layout.tsx          # Root layout
│   │   └── globals.css         # Global styles
│   │
│   ├── components/             # React components
│   │   ├── dashboard/          # Dashboard-specific components
│   │   │   ├── sidebar.tsx     # Navigation sidebar
│   │   │   ├── topbar.tsx      # Top navigation bar
│   │   │   ├── kpi-cards.tsx   # KPI metrics display
│   │   │   └── recent-runs-table.tsx
│   │   ├── ui/                 # shadcn/ui components
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   ├── dialog.tsx
│   │   │   ├── input.tsx
│   │   │   ├── select.tsx
│   │   │   ├── table.tsx
│   │   │   └── ... (20+ components)
│   │   ├── brand-logo.tsx      # Customizable brand logo
│   │   └── theme-provider.tsx  # Theme context
│   │
│   └── lib/                    # Utilities and helpers
│       ├── api.ts              # API client
│       ├── agents.ts           # Agent type definitions
│       ├── config.ts           # Configuration
│       └── utils.ts            # Utility functions
│
├── public/                     # Static assets
├── package.json                # Dependencies
├── tsconfig.json               # TypeScript config
├── tailwind.config.ts          # Tailwind config
└── next.config.ts              # Next.js config
```

### Page Structure

AIOS uses Next.js App Router with the following pages:

| Route | Purpose | Key Features |
|-------|---------|--------------|
| `/` | Dashboard Home | KPIs, health status, recent activity |
| `/agents` | Agent Management | Create, edit, test agents |
| `/analytics` | Analytics | Usage metrics, cost tracking |
| `/approvals` | HITL Queue | Review pending items |
| `/audit` | Audit Logs | Complete interaction history |
| `/onboarding` | Onboarding Wizard | Discover and deploy agents |
| `/runs` | Execution History | View all agent runs |
| `/settings` | System Settings | API keys, policies, system reset |
| `/templates` | Templates | Save/load configurations |
| `/tenants` | Tenant Management | Multi-tenant support |
| `/chat` | Public Chat | Concierge interface |

---

## Getting Started

### 1. Prerequisites

```bash
# Required software
Node.js 18+
npm or yarn
Python 3.11+ (for backend API)
```

### 2. Installation

```bash
# Clone the repository
git clone https://github.com/Shavoni/aios.git
cd aios

# Install backend dependencies
pip install -r requirements.txt

# Start the backend API
python run_api.py
# API runs at http://localhost:8000

# Install frontend dependencies
cd web
npm install

# Start the development server
npm run dev
# Frontend runs at http://localhost:3000
```

### 3. Development Workflow

```bash
# Run development server with hot reload
npm run dev

# Build for production
npm run build

# Run production server
npm start

# Lint code
npm run lint
```

---

## Component Library

AIOS includes a comprehensive component library based on shadcn/ui. All components are:

- **Fully typed** with TypeScript
- **Accessible** (WCAG 2.1 compliant)
- **Customizable** via Tailwind CSS
- **Dark mode ready**
- **Composable** and reusable

### Available Components

#### Form Components
- `<Button>` - Multiple variants (default, destructive, outline, ghost, link)
- `<Input>` - Text input with validation support
- `<Select>` - Dropdown selection
- `<Switch>` - Toggle switch
- `<Textarea>` - Multi-line text input

#### Layout Components
- `<Card>` - Container with header, content, footer
- `<Separator>` - Visual divider
- `<ScrollArea>` - Scrollable container
- `<Tabs>` - Tabbed interface
- `<Sheet>` - Slide-in panel

#### Feedback Components
- `<Dialog>` - Modal dialog
- `<AlertDialog>` - Confirmation dialog
- `<Badge>` - Status indicators
- `<Skeleton>` - Loading placeholders
- `<Sonner>` (toast) - Notifications

#### Data Display
- `<Table>` - Data tables
- `<Avatar>` - User avatars
- `<Tooltip>` - Contextual hints

#### Navigation
- `<DropdownMenu>` - Contextual menus
- Custom `<Sidebar>` - Navigation sidebar
- Custom `<Topbar>` - Top navigation

### Example: Using Components

```tsx
import { Button } from "@/components/ui/button"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"

export default function MyPage() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Agent Configuration</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <Input placeholder="Agent Name" />
          <Button>Create Agent</Button>
        </div>
      </CardContent>
    </Card>
  )
}
```

---

## Customizing the UI

### 1. Changing Colors and Theme

Edit `web/src/app/globals.css`:

```css
:root {
  --background: 0 0% 100%;
  --foreground: 240 10% 3.9%;
  --primary: 240 5.9% 10%;        /* Change primary color */
  --primary-foreground: 0 0% 98%;
  --radius: 0.625rem;              /* Change border radius */
}

.dark {
  --background: 240 10% 3.9%;
  --foreground: 0 0% 98%;
  --primary: 0 0% 98%;             /* Dark mode primary */
  --primary-foreground: 240 5.9% 10%;
}
```

### 2. Customizing the Logo

Edit `web/src/components/brand-logo.tsx`:

```tsx
export function BrandLogo() {
  return (
    <div className="flex items-center gap-2">
      <img src="/your-logo.svg" alt="Your Brand" className="h-8 w-8" />
      <span className="font-bold text-xl">Your Brand</span>
    </div>
  )
}
```

### 3. Modifying the Sidebar

Edit `web/src/components/dashboard/sidebar.tsx`:

```tsx
const navigation = [
  { name: 'Dashboard', href: '/', icon: HomeIcon },
  { name: 'Agents', href: '/agents', icon: BotIcon },
  // Add your custom navigation items
  { name: 'My Custom Page', href: '/custom', icon: CustomIcon },
]
```

### 4. Adding Custom Styles

Use Tailwind CSS utility classes or add custom CSS:

```tsx
// Using Tailwind utilities
<div className="flex items-center justify-between p-4 bg-primary text-primary-foreground rounded-lg">
  Custom styled content
</div>

// Or add custom CSS in globals.css
.my-custom-class {
  background: linear-gradient(to right, #667eea 0%, #764ba2 100%);
  padding: 2rem;
}
```

---

## Creating New Pages

### 1. Create a New Page in the Dashboard

Create `web/src/app/(dashboard)/my-page/page.tsx`:

```tsx
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"

export default function MyPage() {
  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold mb-6">My Custom Page</h1>
      
      <Card>
        <CardHeader>
          <CardTitle>Page Content</CardTitle>
        </CardHeader>
        <CardContent>
          <p>Your content here</p>
          <Button className="mt-4">Action Button</Button>
        </CardContent>
      </Card>
    </div>
  )
}
```

### 2. Add Navigation Link

Update `web/src/components/dashboard/sidebar.tsx`:

```tsx
import { MyIcon } from 'lucide-react'

const navigation = [
  // ... existing items
  { name: 'My Page', href: '/my-page', icon: MyIcon },
]
```

### 3. Create a Standalone Page (Outside Dashboard)

Create `web/src/app/my-standalone/page.tsx`:

```tsx
export default function StandalonePage() {
  return (
    <div className="min-h-screen bg-background">
      <nav className="border-b">
        <div className="container mx-auto p-4">
          <h1 className="text-xl font-bold">Standalone Page</h1>
        </div>
      </nav>
      
      <main className="container mx-auto p-6">
        <p>This page has its own layout</p>
      </main>
    </div>
  )
}
```

---

## Theming & Branding

### Dark Mode Support

AIOS includes built-in dark mode support via `next-themes`:

```tsx
import { useTheme } from "next-themes"

export function ThemeToggle() {
  const { theme, setTheme } = useTheme()
  
  return (
    <button onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>
      Toggle Theme
    </button>
  )
}
```

### Custom Theme Variables

Define custom CSS variables in `globals.css`:

```css
:root {
  --custom-accent: 200 100% 50%;
  --custom-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

/* Use in components */
.my-element {
  background: var(--custom-gradient);
  color: hsl(var(--custom-accent));
}
```

### Component Variants

Use `class-variance-authority` for type-safe variants:

```tsx
import { cva } from "class-variance-authority"

const buttonVariants = cva(
  "rounded-lg font-medium transition-colors",
  {
    variants: {
      intent: {
        primary: "bg-blue-500 text-white hover:bg-blue-600",
        secondary: "bg-gray-200 text-gray-900 hover:bg-gray-300",
        danger: "bg-red-500 text-white hover:bg-red-600",
      },
      size: {
        small: "px-3 py-1.5 text-sm",
        medium: "px-4 py-2 text-base",
        large: "px-6 py-3 text-lg",
      },
    },
    defaultVariants: {
      intent: "primary",
      size: "medium",
    },
  }
)
```

---

## Best Practices

### 1. Type Safety

Always use TypeScript and define proper types:

```tsx
// Define types for your data
interface Agent {
  id: string
  name: string
  domain: string
  status: 'active' | 'inactive'
}

// Type your component props
interface AgentCardProps {
  agent: Agent
  onEdit: (id: string) => void
}

export function AgentCard({ agent, onEdit }: AgentCardProps) {
  return (
    <Card>
      <CardContent>
        <h3>{agent.name}</h3>
        <Button onClick={() => onEdit(agent.id)}>Edit</Button>
      </CardContent>
    </Card>
  )
}
```

### 2. Data Fetching with SWR

Use SWR for efficient data fetching:

```tsx
import useSWR from 'swr'
import { apiClient } from '@/lib/api'

export function AgentList() {
  const { data, error, isLoading } = useSWR('/agents', apiClient.get)
  
  if (isLoading) return <Skeleton />
  if (error) return <div>Error loading agents</div>
  
  return (
    <div>
      {data.map(agent => (
        <AgentCard key={agent.id} agent={agent} />
      ))}
    </div>
  )
}
```

### 3. Consistent Styling

Use the utility function `cn()` for conditional classes:

```tsx
import { cn } from "@/lib/utils"

export function MyComponent({ className, isActive }: Props) {
  return (
    <div className={cn(
      "base-styles p-4 rounded-lg",
      isActive && "bg-blue-500 text-white",
      className
    )}>
      Content
    </div>
  )
}
```

### 4. Accessibility

- Always include proper ARIA labels
- Use semantic HTML elements
- Ensure keyboard navigation works
- Test with screen readers

```tsx
<Button
  aria-label="Delete agent"
  onClick={handleDelete}
>
  <TrashIcon aria-hidden="true" />
</Button>
```

### 5. Loading States

Always show loading states:

```tsx
export function DataComponent() {
  const { data, isLoading } = useSWR('/data')
  
  return (
    <Card>
      <CardContent>
        {isLoading ? (
          <Skeleton className="h-20 w-full" />
        ) : (
          <DataDisplay data={data} />
        )}
      </CardContent>
    </Card>
  )
}
```

---

## Examples

### Example 1: Custom Dashboard Widget

```tsx
// web/src/components/dashboard/custom-widget.tsx
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { TrendingUp } from "lucide-react"
import useSWR from 'swr'

export function CustomWidget() {
  const { data } = useSWR('/api/custom-metrics')
  
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Custom Metric</CardTitle>
        <TrendingUp className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{data?.value || 0}</div>
        <p className="text-xs text-muted-foreground mt-1">
          {data?.description}
        </p>
      </CardContent>
    </Card>
  )
}
```

### Example 2: Form with Validation

```tsx
// web/src/components/agent-form.tsx
'use client'

import { useState } from 'react'
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { toast } from "sonner"

export function AgentForm() {
  const [name, setName] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!name.trim()) {
      toast.error("Name is required")
      return
    }
    
    setIsSubmitting(true)
    try {
      const response = await fetch('/api/agents', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
      })
      
      if (response.ok) {
        toast.success("Agent created successfully")
        setName('')
      }
    } catch (error) {
      toast.error("Failed to create agent")
    } finally {
      setIsSubmitting(false)
    }
  }
  
  return (
    <Card>
      <CardHeader>
        <CardTitle>Create New Agent</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            placeholder="Agent Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            disabled={isSubmitting}
          />
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Creating..." : "Create Agent"}
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}
```

### Example 3: Data Table with Actions

```tsx
// web/src/components/agents-table.tsx
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Edit, Trash } from "lucide-react"

interface Agent {
  id: string
  name: string
  domain: string
  status: 'active' | 'inactive'
}

interface AgentsTableProps {
  agents: Agent[]
  onEdit: (id: string) => void
  onDelete: (id: string) => void
}

export function AgentsTable({ agents, onEdit, onDelete }: AgentsTableProps) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Name</TableHead>
          <TableHead>Domain</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {agents.map((agent) => (
          <TableRow key={agent.id}>
            <TableCell className="font-medium">{agent.name}</TableCell>
            <TableCell>{agent.domain}</TableCell>
            <TableCell>
              <Badge variant={agent.status === 'active' ? 'default' : 'secondary'}>
                {agent.status}
              </Badge>
            </TableCell>
            <TableCell>
              <div className="flex gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onEdit(agent.id)}
                >
                  <Edit className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onDelete(agent.id)}
                >
                  <Trash className="h-4 w-4" />
                </Button>
              </div>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
```

---

## Additional Resources

### Documentation
- **Next.js**: https://nextjs.org/docs
- **React**: https://react.dev
- **shadcn/ui**: https://ui.shadcn.com
- **Tailwind CSS**: https://tailwindcss.com/docs
- **Radix UI**: https://www.radix-ui.com

### AIOS-Specific Documentation
- [Main README](../README.md) - Overview and quick start
- [Developer Handoff](./DEVELOPER_HANDOFF.md) - Architecture deep dive
- [API Documentation](http://localhost:8000/docs) - Backend API reference

### Component Gallery
- Browse all UI components: http://localhost:3000 (after starting dev server)
- See live examples in the dashboard pages

---

## FAQs

### Q: Can I use AIOS to build my own application?
**A:** AIOS is an AI governance platform, not a general-purpose app builder. However, you can:
- Study the codebase as a reference implementation
- Fork and customize it for your needs
- Extract and reuse individual components
- Use the same tech stack for your own projects

### Q: How do I add a new shadcn/ui component?
**A:** Use the shadcn CLI:
```bash
cd web
npx shadcn@latest add [component-name]
# Example: npx shadcn@latest add dropdown-menu
```

### Q: Can I change the styling system?
**A:** Tailwind CSS is deeply integrated. Switching would require significant refactoring. Instead, customize Tailwind via `tailwind.config.ts`.

### Q: How do I deploy the UI?
**A:** AIOS supports standard Next.js deployment:
```bash
cd web
npm run build
npm start
```
For production, use Vercel, Docker, or any Node.js hosting platform.

### Q: Where do I find the API client?
**A:** The API client is in `web/src/lib/api.ts`. Use it to make backend requests:
```tsx
import { apiClient } from '@/lib/api'
const agents = await apiClient.get('/agents')
```

---

## Getting Help

If you need assistance:

1. **Check the docs**: Start with [INDEX.md](./INDEX.md)
2. **Review examples**: Look at existing pages in `web/src/app/`
3. **Read component source**: All components are in `web/src/components/`
4. **Ask questions**: Open an issue on GitHub
5. **Email support**: support@haais.io

---

## Contributing

Want to improve the UI? Contributions are welcome!

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

Please follow the existing code style and patterns.

---

**Built with ❤️ by HAAIS (Human-AI Augmented Intelligence Systems)**
