export interface AttrSpec {
  type: 'text' | 'choice'
  options?: string[]
  default?: string
}

export interface CategoryRule {
  name: string
  attribute_spec: Record<string, AttrSpec>
}

export interface Config {
  vision_configured: boolean
  vision_model: string
  channel: string
  mock_backend_url: string
  rpa_headless: boolean
  batch_limit: number
  ai_title_count: number
  title_max_len: number
  categories: string[]
  category_rules: CategoryRule[]
  attribute_labels: Record<string, string>
}

export interface VisionData {
  category?: string
  color?: string
  material?: string
  style?: string
  source?: string
}

export interface RpaResult {
  success?: boolean
  message?: string
  steps?: string[]
  screenshot?: string
  url?: string
  submitted_at?: string
}

export interface Item {
  id: string
  name: string
  status: string
  error: string
  selected: boolean
  category: string
  attributes: Record<string, string>
  prompts: string[]
  ai_titles: string[]
  rule_title: string
  title_source: string
  manual_title: string
  title: string
  vision: VisionData | null
  placeholders: string[]
  rpa_result: RpaResult | null
  backend_id: string | null
}

export interface ReviewPatch {
  title_source: string
  manual_title: string
  category: string
  attributes: Record<string, string>
  prompts: string[]
  selected: boolean
}

export interface PublishResultItem {
  id: string
  status: string
  error: string
  message: string
  title: string
}

export interface PublishStatus {
  running: boolean
  total: number
  success: number
  failed: number
  error?: string
  items: PublishResultItem[]
}
