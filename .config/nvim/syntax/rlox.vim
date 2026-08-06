if exists("b:current_syntax")
  finish
endif

syntax sync fromstart
syntax case match

syntax keyword rloxKeyword let rec fn if else while return and or struct nil
syntax keyword rloxBoolean true false
syntax match rloxOperator "[+\-*/<>=!%]"
syntax match rloxOperator "[{}[\](),;]"
syntax match rloxNumber "\<\d\+\(\.\d\+\)\?\>"
syntax region rloxString start=/"/ skip=/\\"/ end=/"/ contains=rloxStringEscape keepend
syntax match rloxStringEscape "\\." contained
syntax match rloxComment "//.*$" oneline
syntax region rloxComment start="/\*" end="\*/" keepend

highlight rloxKeyword guifg=#43728C
highlight rloxBoolean guifg=#E4BC7E
highlight rloxOperator guifg=#8F8CA8
highlight rloxString guifg=#E4BC7E
highlight rloxNumber guifg=#E4BC7E
highlight rloxComment guifg=#8F8CA8
highlight rloxStringEscape guifg=#E4BC7E

let b:current_syntax = "rlox"
