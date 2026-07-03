package com.example.lddc.common.models.enums

import kotlinx.serialization.Serializable

@Serializable
enum class Source {
    MULTI,
    QM,
    KG,
    NE,
    LRCLIB,
    LOCAL;

}
