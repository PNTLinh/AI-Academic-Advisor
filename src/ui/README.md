# Student Academic Advisor 🎓

An intelligent student academic planning application built with modern web technologies to help students plan their courses, track progress, and receive personalized academic guidance.

## Features

- 🤖 **AI Academic Advisor Chat** - Get personalized course recommendations and academic guidance
- 📊 **Student Profile Dashboard** - Track GPA, credits earned, academic standing, and transcript
- 🗺️ **Smart Roadmap** - Visualize your academic journey and course sequencing
- 📝 **Course Planning** - Browse and select courses with priority levels
- 💬 **Study Goals Configuration** - Set effort levels and availability constraints
- 🌓 **Dark/Light Theme** - Beautiful UI with theme support
- 📱 **Responsive Design** - Works seamlessly on desktop and mobile devices

## Pages

- **`/`** - Home page with course recommendations
- **`/advisor`** - Main AI advisor chat interface (primary page)
- **`/planner`** - Course planning and scheduling tool

## Tech Stack

- **Frontend Framework**: Next.js 16.2
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **UI Components**: Radix UI with shadcn/ui
- **Icons**: Lucide React
- **Form Handling**: React Hook Form
- **State Management**: React Hooks

## Getting Started

### Prerequisites

- Node.js 18+ installed
- Package manager: `pnpm`, `npm`, or `yarn`

### Installation

1. **Install dependencies:**
   ```bash
   pnpm install
   # or
   npm install
   ```

2. **Run development server:**
   ```bash
   pnpm dev
   # or
   npm run dev
   ```

3. **Open your browser:**
   Navigate to [http://localhost:3000](http://localhost:3000)
   - Home page: http://localhost:3000
   - Advisor: http://localhost:3000/advisor
   - Planner: http://localhost:3000/planner

## Available Scripts

```bash
pnpm dev      # Start development server
pnpm build    # Build for production
pnpm start    # Run production build
pnpm lint     # Run ESLint checks
```

## Project Structure

```
├── app/                          # Next.js app directory
│   ├── page.tsx                 # Home/courses page
│   ├── layout.tsx               # Root layout
│   ├── advisor/                 # Advisor chat interface
│   └── planner/                 # Course planning interface
├── components/                   # Reusable React components
│   ├── chat-message.tsx         # Chat message display
│   ├── course-card.tsx          # Course card component
│   ├── smart-roadmap.tsx        # Academic roadmap visualization
│   ├── student-profile-panel.tsx # Student profile display
│   ├── study-goals-widget.tsx   # Study goals configuration
│   └── ui/                      # shadcn/ui components
├── hooks/                       # Custom React hooks
├── lib/                         # Utility functions
└── styles/                      # Global styles
```

## Key Components

- **ChatMessage** - Displays chat messages with AI advisor
- **CourseCard** - Shows individual course information with priority levels
- **StudentProfilePanel** - Displays student GPA, credits, and academic standing
- **SmartRoadmap** - Visualizes course prerequisites and academic progress
- **StudyGoalsWidget** - Allows students to set effort levels and availability

## Features Roadmap

- [ ] Backend API integration for real student data
- [ ] Database for storing student profiles and transcripts
- [ ] Advanced AI recommendations using ML models
- [ ] Calendar integration for course scheduling
- [ ] Grade prediction based on academic performance
- [ ] Degree requirements tracking

## License

Private project

## Support

For questions or issues, please contact the development team.
