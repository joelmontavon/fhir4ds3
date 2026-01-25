/*
 * FHIRPath Grammar for ANTLR 4
 *
 * Forked from fhirpath-py and customized for FHIR4DS integration.
 * Original source: https://github.com/beda-software/fhirpath-py
 *
 * This grammar defines the syntax for FHIRPath expressions,
 * a query and navigation language for FHIR resources.
 */

grammar FHIRPath;

// Parser Rules

expression
    : termExpression                                                    #termExpressionTerm
    | expression '.' invocation                                         #invocationTerm
    | expression '[' expression ']'                                     #indexerTerm
    | expression op=('*' | '/' | 'div' | 'mod') expression             #multiplicativeExpressionTerm
    | expression op=('+' | '-' | '&') expression                       #additiveExpressionTerm
    | expression op='is' typeSpecifier                                  #typeExpressionTerm
    | expression op='as' typeSpecifier                                  #typeExpressionTerm
    | expression op=('|' | 'union') expression                         #unionExpressionTerm
    | expression op=('=' | '!=' | '~' | '!~') expression               #equalityExpressionTerm
    | expression op=('<=' | '<' | '>' | '>=') expression               #inequalityExpressionTerm
    | expression op=('in' | 'contains') expression                     #membershipExpressionTerm
    | expression op='and' expression                                    #andExpressionTerm
    | expression op=('or' | 'xor') expression                          #orExpressionTerm
    | expression op='implies' expression                                #impliesExpressionTerm
    ;

termExpression
    : invocation                                            #invocationTerm
    | literal                                               #literalTerm
    | externalConstant                                      #externalConstantTerm
    | '(' expression ')'                                    #parenthesizedTerm
    ;

literal
    : nullLiteral                                           #nullLiteralTerm
    | booleanLiteral                                        #booleanLiteralTerm
    | stringLiteral                                         #stringLiteralTerm
    | numberLiteral                                         #numberLiteralTerm
    | dateTimeLiteral                                       #dateTimeLiteralTerm
    | timeLiteral                                           #timeLiteralTerm
    | quantityLiteral                                       #quantityLiteralTerm
    ;

externalConstant
    : '%' identifier
    | '%' stringLiteral
    ;

invocation
    : memberInvocation
    | functionInvocation
    ;

memberInvocation
    : identifier
    ;

functionInvocation
    : identifier '(' funcParamList? ')'
    ;

funcParamList
    : expression (',' expression)*
    ;

typeSpecifier
    : qualifiedIdentifier
    ;

qualifiedIdentifier
    : identifier ('.' identifier)*
    ;

identifier
    : IDENTIFIER
    | DELIMITEDIDENTIFIER
    | 'as'
    | 'is'
    | 'contains'
    | 'in'
    | 'div'
    | 'mod'
    | 'and'
    | 'or'
    | 'xor'
    | 'implies'
    | 'union'
    ;

// Literal Rules

nullLiteral
    : 'null'
    ;

booleanLiteral
    : 'true'
    | 'false'
    ;

stringLiteral
    : STRING
    ;

numberLiteral
    : NUMBER
    ;

dateTimeLiteral
    : DATETIME
    ;

timeLiteral
    : TIME
    ;

quantityLiteral
    : NUMBER unit?
    ;

unit
    : dateTimePrecision
    | pluralDateTimePrecision
    | stringLiteral
    ;

dateTimePrecision
    : 'year' | 'month' | 'week' | 'day' | 'hour' | 'minute' | 'second' | 'millisecond'
    ;

pluralDateTimePrecision
    : 'years' | 'months' | 'weeks' | 'days' | 'hours' | 'minutes' | 'seconds' | 'milliseconds'
    ;

// Lexer Rules

IDENTIFIER
    : ([A-Za-z] | '_')([A-Za-z0-9] | '_')*
    ;

DELIMITEDIDENTIFIER
    : '`' (ESC | ~[`\\])* '`'
    ;

STRING
    : '\'' (ESC | ~[\'\\])* '\''
    ;

NUMBER
    : [0-9]+('.' [0-9]+)?
    ;

DATETIME
    : '@' [0-9][0-9][0-9][0-9] ('-'[0-9][0-9] ('-'[0-9][0-9] ('T' [0-9][0-9] (':'[0-9][0-9] (':'[0-9][0-9] ('.'[0-9]+)?)?)? ('Z' | ('+' | '-') [0-9][0-9]':'[0-9][0-9])?)?)?)? 'T'?
    ;

TIME
    : '@' 'T' [0-9][0-9] (':'[0-9][0-9] (':'[0-9][0-9] ('.'[0-9]+)?)?)?
    ;

fragment ESC
    : '\\' ([`'\\] | 'r' | 'n' | 't' | 'u' [0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f])
    ;

WS
    : [ \r\n\t]+ -> skip
    ;

COMMENT
    : '/*' .*? '*/' -> skip
    ;

LINE_COMMENT
    : '//' ~[\r\n]* -> skip
    ;