# BAML - Boundary Markup Language

BAML is a domain-specific language designed for generating structured outputs
from Large Language Models (LLMs) with a focus on developer experience. It
provides a type-safe way to define prompts, expected outputs, and client
integrations.

## Core Features

- Type-safe outputs, even when streaming structured data
- Flexibility to work with any LLM, language, and schema
- Fast developer experience with a VSCode playground
- Structured output capabilities that can outperform OpenAI with their own
  models

## Core Language Elements

### Types

BAML supports various data types:

1. **Primitive Types**

   - `bool`, `int`, `float`, `string`, `null`

2. **Literal Types** (v0.61.0+)

   - Constrained primitive values: `"bug" | "enhancement"`

3. **Multimodal Types**

   - `image`: For models supporting image inputs
   - `audio`: For models supporting audio inputs

4. **Composite/Structured Types**

   - `enum`: A set of named constants
   - `class`: User-defined complex data structures
   - `Optional (?)`: Values that might be absent (`int?`)
   - `Union (|)`: Types that can hold multiple possible type values
     (`int | string`)
   - `List/Array ([])`: Collections of elements (`string[]`)
   - `Map`: String or enum key-value mappings (`map<string, int>`)

5. **Type Aliases** (v0.71.0+)
   - Alternative names for existing types: `type Graph = map<string, string[]>`

### Enums

Enums are useful for classification tasks:

```baml
enum SentimentCategory {
  Positive @alias("k1") // use abstract symbols to force classification based on description instead of the label
  @description(#"
    Statement expresses clear positive sentiment:
      - Indicates approval or satisfaction
      - Expresses optimism about outcomes
      - Shows enthusiasm or excitement
  "#)

  Negative @alias("k2")
  @description(#"
    Statement expresses clear negative sentiment:
      - Indicates disapproval or dissatisfaction
      - Expresses pessimism about outcomes
      - Shows frustration or disappointment
  "#)

  Neutral @alias("k3")
  @description("Statement lacks clear sentiment indicators")

  @@dynamic  // Allows adding more values at runtime
}
```

Enum attributes include:

- Field-level: `@alias`, `@description`, `@skip`
- Block-level: `@@alias`, `@@dynamic`

### Classes

Classes define structured data:

```baml
class DocumentMetadata {
  doc_id string @description("The unique identifier of the document")
  title string @description("Document title")
  created_at float @description("Creation timestamp")
  tags string[] @description("Associated tags")
}

class AnalysisResult {
  sentiment SentimentCategory
  confidence float @description("Confidence score between 0 and 1")
  key_points string[] @description("List of extracted key points")
  metadata DocumentMetadata
}
```

Class attributes include:

- Field-level: `@alias`, `@description`, `@check`, `@assert`
- Block-level: `@@dynamic`

### Functions

Functions in BAML define the contract between your application and AI models:

```baml
function AnalyzeDocument(document_text: string) -> AnalysisResult {
  client GPT4Turbo
  prompt #"
    Analyze the sentiment and extract key points from the following document:

    {{ document_text }}

    Provide detailed reasoning before making your analysis, addressing:
    1. Overall tone and language patterns
    2. Specific phrases indicating sentiment
    3. Main topics and arguments presented

    Example reasoning:
    - The document uses predominantly positive language with phrases like "excellent opportunity"
    - Multiple references to benefits and advantages suggest positive sentiment
    - Key topics include product features, market positioning, and competitive advantages

    {{ ctx.output_format }}

    ANALYSIS GUIDELINES:
    1. Base sentiment classification solely on textual evidence
    2. Extract only explicitly stated key points
    3. Assign confidence scores based on clarity of sentiment indicators

    Response:
  "#
}
```

Functions support:

- Input parameters with typed arguments
- Return type specifications (including unions:
  `-> (ResultType1 | ResultType2)[]`)
- Client specification
- Prompt template with Jinja-like syntax

### Clients

BAML supports multiple LLM clients through client declarations:

```baml
client<llm> GPT4Turbo {
    provider "openai"
    options {
        model "gpt-4-turbo"
        api_key env.OPENAI_API_KEY
        temperature 0.2
        max_tokens 2000
    }
}
```

### Templating

BAML uses a Jinja-like templating system for dynamic prompt generation with
special variables:

- `{{ variable_name }}`: Insert variable content
- `{% for ... %}{% endfor %}`: Control structures
- `{{ ctx.output_format }}`: Automatically generates format instructions based
  on return type
- Block strings: `#"..."#` for multi-line prompts

Example template string:

```baml
template_string FormatUserMessages(messages: Message[]) #"
  {% for m in messages %}
    {{ _.role(m.role) }}
    {{ m.content }}
  {% endfor %}
"#
```

### Dynamic Types

The `@@dynamic` attribute allows runtime modification of types:

```baml
enum ProductCategory {
  Electronics
  Clothing
  Books
  @@dynamic  // Allows adding more values at runtime
}
```

TypeBuilder can create or modify output schemas at runtime:

```python
tb = TypeBuilder()
tb.ProductCategory.add_value('HomeAppliances')
tb.ProductCategory.add_value('OfficeSupplies')
```

## Complex Example

Here's a more complex example showing BAML capabilities:

```baml
enum RecommendationType {
  Product @description("Recommendation for a specific product")
  Category @description("Recommendation for a product category")
  Bundle @description("Recommendation for a product bundle")
}

class RecommendationSource {
  source_id string
  confidence float @description("Confidence score between 0-1")
  rationale string @description("Why this source supports the recommendation")
}

class ProductRecommendation {
  type RecommendationType
  name string
  description string
  price_range string @description("Approximate price range")
  key_benefits string[] @description("List of main benefits")
  sources RecommendationSource[] @description("Evidence supporting this recommendation")
}

function GenerateRecommendations(user_profile: string, purchase_history: string) -> ProductRecommendation[] {
  client GPT4Turbo
  prompt #"
    Generate personalized product recommendations based on the following information:

    ## User Profile
    {{ user_profile }}

    ## Purchase History
    {{ purchase_history }}

    Think carefully about patterns in the user's purchases and preferences before making recommendations.
    Consider factors like:
    - Price sensitivity
    - Brand preferences
    - Product categories of interest
    - Frequency of purchases

    {{ ctx.output_format }}

    RECOMMENDATION GUIDELINES:
    1. Provide clear rationale for each recommendation
    2. Prioritize products that align with demonstrated preferences
    3. Include a mix of safe recommendations and novel suggestions
    4. Ensure each recommendation has solid supporting evidence

    Response:
  "#
}
```

## Code Generation

BAML can generate client code for different languages:

```baml
generator target {
    output_type "python/pydantic"
    output_dir "../"
    default_client_mode "sync"
    version "0.76.2"
}
```

For React/Next.js, it generates type-safe hooks for each BAML function with
streaming support.

## Environment Variables

Environment variables can be referenced using the `env.` prefix:

```baml
api_key env.OPENAI_API_KEY
```

## Motivation

BAML addresses the lack of tooling for prompt engineering. Traditional
approaches treat prompts as simple strings, lacking:

- Type safety
- Hot-reloading or previews
- Linting

BAML provides the ideal abstraction layer for prompt engineering, similar to how
TSX/JSX improved web development.
