; BAML Tree-sitter Highlights
; Comprehensive syntax highlighting for BAML language

; Comments
(comment) @comment
(doc_comment) @comment.documentation  
(block_comment) @comment.block

; Keywords - Now they're distinct tokens!
"class" @keyword.type
"enum" @keyword.type
"type" @keyword.type
"dynamic" @keyword.modifier

"function" @keyword.function
"test" @keyword.function
"client" @keyword.function
"generator" @keyword.function
"retry_policy" @keyword.function

"template_string" @keyword
"string_template" @keyword
"type_builder" @keyword

"fn" @keyword.function
"let" @keyword
"map" @keyword.type

; Boolean literals
((identifier) @constant.builtin.boolean
  (#match? @constant.builtin.boolean "^(true|false)$"))

((identifier) @constant.builtin
  (#match? @constant.builtin "^(null)$"))

; Operators
"=" @operator
"->" @operator
"=>" @operator
"|" @operator
"?" @operator
".." @operator
"." @operator
"::" @operator
":" @operator

; Punctuation
"{" @punctuation.bracket
"}" @punctuation.bracket
"[" @punctuation.bracket
"]" @punctuation.bracket
"[]" @punctuation.bracket
"(" @punctuation.bracket
")" @punctuation.bracket
"<" @punctuation.bracket
">" @punctuation.bracket

"," @punctuation.delimiter
";" @punctuation.delimiter

; Attributes
"@" @punctuation.special
"@@" @punctuation.special
(field_attribute (identifier) @attribute)
(block_attribute (identifier) @attribute)

; Strings
(quoted_string_literal) @string
(unquoted_string_literal) @string  
; Raw strings - make the entire content one color (no parsing inside)
(raw_string_literal) @string.special

; String literal wrapper
(string_literal) @string

; Numbers
(numeric_literal) @number

; Function definitions and calls
(expr_fn
  name: (identifier) @function)

(value_expression_block
  keyword: (value_expression_keyword) @keyword.function
  name: (identifier) @function)

(fn_app
  function_name: (identifier) @function.call)

; Type definitions
(type_expression_block
  block_keyword: _ @keyword.type
  name: (identifier) @type.definition)
  
(type_alias
  "type" @keyword.type
  name: (identifier) @type.definition)

; Template definitions
(template_declaration
  name: (identifier) @function.special)

; Field/property names
(type_expression
  name: (identifier) @property)
  
(value_expression
  name: (identifier) @property)

(map_entry
  key: (map_key (identifier) @property))

; Class constructors
(class_constructor
  class_name: (identifier) @type)

(class_field_value_pair
  field_name: (identifier) @property)

; Type references
(base_type (identifier) @type)

; Map types
(map_type 
  "map" @keyword.type
  key_type: (_) @type
  value_type: (_) @type)

; Parameters
(named_argument
  name: (identifier) @parameter)

(named_argument_list
  (named_argument
    type: (_) @type))

; Lambda expressions
(lambda
  params: (named_argument_list
    (named_argument
      name: (identifier) @parameter)))

; Let bindings
(let_expr
  "let" @keyword
  name: (identifier) @variable.definition)

; Special built-in types (high priority)
((base_type (identifier) @type.builtin)
  (#match? @type.builtin "^(string|int|int32|int64|float|float32|float64|bool|boolean|any|null|image|audio)$"))

; Special identifiers
((identifier) @variable.builtin
  (#match? @variable.builtin "^(this|ctx|env)$"))

; Namespace and path identifiers
(namespaced_identifier) @namespace
(path_identifier) @module

; Default identifier highlighting (lowest priority)
(identifier) @variable

; Error handling - make errors less intrusive  
(ERROR) @comment

; Override: Remove highlighting from identifiers that look like template vars
((identifier) @none
  (#match? @none "^[a-z_][a-zA-Z0-9_]*\\.[a-z_][a-zA-Z0-9_]*"))

; Template interpolation is handled via Lua syntax module
; to properly override TreeSitter highlighting