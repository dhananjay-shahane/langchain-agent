# Overview

This is a LangChain MCP (Model Context Protocol) Agent system designed for processing and analyzing LAS (Log ASCII Standard) files from the oil and gas industry. The application provides an intelligent chat interface where users can interact with AI agents to analyze well log data, generate visualizations, and create reports. It's built as a full-stack web application with real-time communication capabilities.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture
- **Framework**: React with TypeScript using Vite as the build tool
- **UI Library**: Shadcn/ui components built on Radix UI primitives with Tailwind CSS for styling
- **State Management**: TanStack Query (React Query) for server state management
- **Routing**: Wouter for lightweight client-side routing
- **Real-time Communication**: Socket.io client for live updates

## Backend Architecture
- **Framework**: Express.js with TypeScript running on Node.js
- **API Design**: RESTful endpoints with real-time WebSocket support via Socket.io
- **Data Storage**: In-memory storage with Drizzle ORM schema definitions (prepared for PostgreSQL)
- **File Processing**: Python scripts for LAS file analysis and plotting using matplotlib
- **Agent System**: LangChain integration with MCP (Model Context Protocol) for AI agent capabilities

## AI Agent Integration
- **LangChain**: Primary framework for building conversational AI agents
- **MCP Support**: Model Context Protocol for tool integration and external system connections
- **Multi-Provider Support**: Configurable AI providers (Ollama, OpenAI, Anthropic)
- **Tool System**: Custom Python tools for LAS file analysis, plotting, and formation analysis

## Data Processing Pipeline
- **File Monitoring**: Automatic detection of new LAS files via file system watchers
- **Email Integration**: Python-based email monitor for processing LAS file attachments
- **Analysis Tools**: Specialized scripts for formation analysis, log plotting, and data visualization
- **Output Management**: Automated storage and serving of generated plots and reports

## Real-time Features
- **WebSocket Communication**: Live updates for new files, agent responses, and configuration changes
- **File System Monitoring**: Automatic detection and processing of new LAS files
- **Progress Tracking**: Real-time status updates for long-running analysis tasks

## Security & Configuration
- **Environment-based Configuration**: Secure storage of API keys and database credentials
- **CORS Handling**: Proper cross-origin resource sharing configuration
- **File Upload Security**: Sanitized file handling and storage
- **Agent Configuration Security**: All hardcoded endpoint URLs removed from codebase (Sept 2025)
- **Dashboard Management**: Agent provider, model, and endpoint configuration via secure UI

# External Dependencies

## Core Infrastructure
- **Neon Database**: PostgreSQL database hosting (configured via DATABASE_URL)
- **Drizzle ORM**: Database query builder and migration system

## AI & ML Services
- **Ollama**: Local LLM hosting (configurable endpoint)
- **OpenAI API**: GPT model access (requires OPENAI_API_KEY)
- **Anthropic Claude**: Alternative AI provider (requires ANTHROPIC_API_KEY)

## Email Services
- **IMAP Integration**: Email monitoring for LAS file attachments
- **Gmail/IMAP Servers**: Configurable via EMAIL_USER and EMAIL_PASS environment variables

## Development Tools
- **Replit Integration**: Development environment with live reloading and error overlay
- **Vite Development Server**: Hot module replacement and development proxy

## Python Dependencies
- **Scientific Computing**: NumPy, Matplotlib for data analysis and visualization
- **LangChain Libraries**: Core framework, provider adapters, and MCP integration
- **Email Processing**: imap-tools for email attachment monitoring
- **File System**: chokidar for Node.js file watching, pathlib for Python file operations

## UI & Styling
- **Tailwind CSS**: Utility-first CSS framework with custom design system
- **Radix UI**: Accessible component primitives
- **Google Fonts**: Inter, Geist Mono, and other typography options
- **Lucide Icons**: Consistent icon system throughout the application