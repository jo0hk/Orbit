
package com.example.demo.entity;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;

import java.util.Locale;

public enum Emotion {

    HAPPY,
    SAD,
    ANGRY,
    CALM;

    @JsonCreator
    public static Emotion fromString(String value) {

        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException("감정값이 비어 있습니다.");
        }

        return Emotion.valueOf(
                value.trim().toUpperCase(Locale.ROOT)
        );
    }

    @JsonValue
    public String toJson() {
        return name().toLowerCase(Locale.ROOT);
    }
}
