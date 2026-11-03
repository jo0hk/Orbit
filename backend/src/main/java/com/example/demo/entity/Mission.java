package com.example.demo.entity;

import jakarta.persistence.*;

@Entity
@Table(name = "missions")
public class Mission {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true)
    private Integer stage;

    @Column(nullable = false)
    private String title;

    @Column(length = 1000)
    private String description;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private MissionType missionType;

    protected Mission() {
    }

    public Mission(
            Integer stage,
            String title,
            String description,
            MissionType missionType
    ) {
        this.stage = stage;
        this.title = title;
        this.description = description;
        this.missionType = missionType;
    }

    public Long getId() {
        return id;
    }

    public Integer getStage() {
        return stage;
    }

    public String getTitle() {
        return title;
    }

    public String getDescription() {
        return description;
    }

    public MissionType getMissionType() {
        return missionType;
    }
}