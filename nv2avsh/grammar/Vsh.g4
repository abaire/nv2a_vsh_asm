// Grammar for the nv2a vertex shader language.
grammar Vsh;

program : statement* EOF ;
statement :
    NEWLINE
    | combined_operation
    | operation
    | uniform_declaration
    ;

combined_operation :
    operation NEWLINE* COMBINE NEWLINE* operation (NEWLINE* COMBINE NEWLINE* operation)?
    ;

operation :
    op_add
    | op_arl
    | op_dp3
    | op_dp4
    | op_dph
    | op_dst
    | op_expp
    | op_lit
    | op_logp
    | op_mad
    | op_max
    | op_min
    | op_mov
    | op_mul
    | op_rcc
    | op_rcp
    | op_rsq
    | op_sge
    | op_slt
    | op_sub
    ;

op_add : OP_ADD p_out_in_in ;
op_arl : OP_ARL p_a0_in ;
op_dp3 : OP_DP3 p_out_in_in ;
op_dp4 : OP_DP4 p_out_in_in ;
op_dph : OP_DPH p_out_in_in ;
op_dst : OP_DST p_out_in_in ;
op_expp : OP_EXPP p_out_in ;
op_lit : OP_LIT p_out_in ;
op_logp : OP_LOGP p_out_in ;
op_mad : OP_MAD p_out_in_in_in ;
op_max : OP_MAX p_out_in_in ;
op_min : OP_MIN p_out_in_in ;
op_mov : OP_MOV p_out_in ;
op_mul : OP_MUL p_out_in_in ;
op_rcc : OP_RCC p_out_in ;
op_rcp : OP_RCP p_out_in ;
op_rsq : OP_RSQ p_out_in ;
op_sge : OP_SGE p_out_in_in ;
op_slt : OP_SLT p_out_in_in ;
op_sub : OP_SUB p_out_in_in ;

p_a0_in : p_a0_output SEP p_input ;
p_out_in : p_output SEP p_input ;
p_out_in_in : p_output SEP p_input SEP p_input ;
p_out_in_in_in : p_output SEP p_input SEP p_input SEP p_input ;

reg_const :
    REG_Cx_BARE
    | REG_Cx_BRACKETED
    | REG_Cx_RELATIVE_A_FIRST
    | REG_Cx_RELATIVE_A_SECOND
    ;

uniform_const :
    UNIFORM_IDENTIFIER ('[' WHITESPACE* INTEGER WHITESPACE* ']')?
    ;

p_a0_output: REG_A0 DESTINATION_MASK? ;
p_output : (REG_Rx | REG_OUTPUT | reg_const | uniform_const) DESTINATION_MASK? ;
// Input swizzling is more permissive than destination masks, but the matching is
// overlapping so both tokens are accepted.
p_input_raw : (REG_Rx | REG_INPUT | REG_R12 | reg_const | uniform_const) (SWIZZLE_MASK | DESTINATION_MASK)? ;
p_input_negated : NEGATE p_input_raw ;
p_input : p_input_raw | p_input_negated ;

uniform_type :
    TYPE_MATRIX4
    | TYPE_VECTOR
    ;

uniform_declaration :
    UNIFORM_IDENTIFIER uniform_type INTEGER
    ;

NEGATE : '-' ;
INTEGER : [0-9]+ ;
FLOAT : [0-9]+ ('.' [0-9]*)? 'f'? ;
fragment COMP_X : 'x' | 'X' | 'r' | 'R' ;
fragment COMP_Y : 'y' | 'Y' | 'g' | 'G' ;
fragment COMP_Z : 'z' | 'Z' | 'b' | 'B' ;
fragment COMP_W : 'w' | 'W' | 'a' | 'A' ;

fragment DEST_MASK_X : COMP_X COMP_Y? COMP_Z? COMP_W? ;
fragment DEST_MASK_Y : COMP_Y COMP_Z? COMP_W? ;
fragment DEST_MASK_Z : COMP_Z COMP_W? ;
DESTINATION_MASK : '.' (DEST_MASK_X | DEST_MASK_Y | DEST_MASK_Z | COMP_W) ;

fragment SWIZZLE_MASK_COMPONENT : COMP_X | COMP_Y | COMP_Z | COMP_W ;
SWIZZLE_MASK : '.' SWIZZLE_MASK_COMPONENT SWIZZLE_MASK_COMPONENT? SWIZZLE_MASK_COMPONENT? SWIZZLE_MASK_COMPONENT? ;

// Input registers

// TODO: Consider using c-96 to c95 instead of c0 to c191
fragment REG_Cx_INDEX : ([0-9] | [1-9][0-9] | '1'[0-8][0-9] | '19'[0-1]) ;
REG_Cx_BARE : [cC] REG_Cx_INDEX ;
fragment REG_Cx_BRACKET_START : 'c[' | 'C[' ;
fragment REG_Cx_BRACKET_END : ']' ;
REG_Cx_BRACKETED : REG_Cx_BRACKET_START REG_Cx_INDEX REG_Cx_BRACKET_END ;
REG_Cx_RELATIVE_A_FIRST : REG_Cx_BRACKET_START WHITESPACE* 'A0' WHITESPACE* COMBINE WHITESPACE* REG_Cx_INDEX WHITESPACE* REG_Cx_BRACKET_END ;
REG_Cx_RELATIVE_A_SECOND : REG_Cx_BRACKET_START WHITESPACE* REG_Cx_INDEX WHITESPACE* COMBINE WHITESPACE* 'A0' WHITESPACE* REG_Cx_BRACKET_END ;
fragment REG_I_POS : [vV]'0' | 'iPos' ;
fragment REG_I_WEIGHT : [vV]'1' | 'iWeight' ;
fragment REG_I_NORMAL : [vV]'2' | 'iNormal' ;
fragment REG_I_DIFFUSE : [vV]'3' | 'iDiffuse' ;
fragment REG_I_SPECULAR : [vV]'4' | 'iSpecular' ;
fragment REG_I_FOG : [vV]'5' | 'iFog' ;
fragment REG_V6 : [vV]'6' | 'iPts' ;
fragment REG_I_BACK_DIFFUSE : [vV]'7' | 'iBackDiffuse' ;
fragment REG_I_BACK_SPECULAR : [vV]'8' | 'iBackSpecular' ;
fragment REG_I_TEX0 : [vV]'9' | 'iTex0' ;
fragment REG_I_TEX1 : [vV]'10' | 'iTex1' ;
fragment REG_I_TEX2 : [vV]'11' | 'iTex2' ;
fragment REG_I_TEX3 : [vV]'12' | 'iTex3' ;
fragment REG_V13 : [vV]'13' ;
fragment REG_V14 : [vV]'14' ;
fragment REG_V15 : [vV]'15' ;

// R12 is a special input-only alias of 'oPos'
REG_R12 : [rR]'12' ;

REG_INPUT :
    REG_I_POS
    | REG_I_WEIGHT
    | REG_I_NORMAL
    | REG_I_DIFFUSE
    | REG_I_SPECULAR
    | REG_I_FOG
    | REG_V6
    | REG_I_BACK_DIFFUSE
    | REG_I_BACK_SPECULAR
    | REG_I_TEX0
    | REG_I_TEX1
    | REG_I_TEX2
    | REG_I_TEX3
    | REG_V13
    | REG_V14
    | REG_V15
    ;

// Output registers

fragment REG_O_BACK_DIFFUSE : 'oB0' | 'oBackDiffuse' ;
fragment REG_O_BACK_SPECULAR : 'oB1' | 'oBackSpecular' ;
fragment REG_O_DIFFUSE : 'oD0' | 'oDiffuse' ;
fragment REG_O_SPECULAR : 'oD1' | 'oSpecular' ;
fragment REG_O_FOG : 'oFog' ;
fragment REG_O_POS : 'oPos' ;
fragment REG_O_POINT_SIZE : 'oPts' ;
fragment REG_O_TEX0 : 'oTex0' | 'oT0' ;
fragment REG_O_TEX1 : 'oTex1' | 'oT1' ;
fragment REG_O_TEX2 : 'oTex2' | 'oT2' ;
fragment REG_O_TEX3 : 'oTex3' | 'oT3' ;

REG_OUTPUT :
    REG_O_BACK_DIFFUSE
    | REG_O_BACK_SPECULAR
    | REG_O_DIFFUSE
    | REG_O_SPECULAR
    | REG_O_FOG
    | REG_O_POS
    | REG_O_POINT_SIZE
    | REG_O_TEX0
    | REG_O_TEX1
    | REG_O_TEX2
    | REG_O_TEX3
     ;

// General purpose registers
REG_Rx : [rR] ([0-9] | '1'[0-1]) ;
REG_A0 : [aA]'0' ;

// Define constants
DEF : ('DEF' | 'def') FLOAT ;

// Operations

OP_NOP : 'NOP' | 'nop' ;

// MAC
OP_ADD : 'ADD' | 'add' ;
OP_DP3 : 'DP3' | 'dp3' ;
OP_DP4 : 'DP4' | 'dp4' ;
OP_DST : 'DST' | 'dst' ;
OP_MAD : 'MAD' | 'mad' ;
OP_MAX : 'MAX' | 'max' ;
OP_MIN : 'MIN' | 'min' ;
OP_MOV : 'MOV' | 'mov' ;
OP_MUL : 'MUL' | 'mul' ;
OP_SGE : 'SGE' | 'sge' ;
OP_SLT : 'SLT' | 'slt' ;
OP_SUB : 'SUB' | 'sub' ;

OP_ARL : 'ARL' | 'arl' ;
OP_DPH : 'DPH' | 'dph' ;

// ILU
OP_EXPP : 'EXPP' | 'expp' ;
OP_LIT : 'LIT' | 'lit' ;
OP_LOGP : 'LOGP' | 'logp' ;
OP_RCP : 'RCP' | 'rcp' ;
OP_RSQ : 'RSQ' | 'rsq' ;

OP_RCC : 'RCC' | 'rcc' ;

UNIFORM_DEFINITION : '%' ('uniform' | 'UNIFORM') ;
TYPE_VECTOR : 'vector' | 'VECTOR' ;
TYPE_MATRIX4 : ('matrix' | 'MATRIX') '4' ;

// Macro identfiers must be at least 2 characters and start with a #
// followed by any number of letters, numbers, or underscores.
UNIFORM_IDENTIFIER : '#'[a-zA-Z0-9_]+ ;

COMBINE : '+' ;
NEWLINE : ('\r\n' | '\n' | '\r')+ ;
SEP : ',' ;
SEP_MULTILINE : SEP NEWLINE ;

WHITESPACE : [ \t]+ -> skip ;
LINE_COMMENT : ('//' | ';') .*? NEWLINE -> skip ;
BLOCK_COMMENT : '/*' .*? '*/' NEWLINE -> skip ;


BAD_INPUT : .  ;
