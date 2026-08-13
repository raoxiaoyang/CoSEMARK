from .utils import *
from .num_ruleset import *
from .str_ruleset import *
from .container_ruleset import *



operators = {

    "num": {
        
        "get_identifiers": get_numeric_identifiers_list_c,
        "gen_marked_code": generate_numeric_watermarked_code_c,
        "get_assignments": get_numeric_assignments_c,

        "PTI_1V_a0": pythagorean_trigonometric_identity_OneVar_AddZero_C,
        "PTI_1V_at": pythagorean_trigonometric_identity_OneVar_Assert_C,
        "PTI_2V_a0": pythagorean_trigonometric_identity_TwoVars_AddZero_C,
    },

    "str": {

        "get_identifiers": get_character_identifiers_list_c,
        "gen_marked_code": generate_character_watermarked_code_c,
        "get_assignments": get_character_assignments_c,

        "REM_1V_a0": regular_expression_match_OneVar_Assert_C,

    }
}