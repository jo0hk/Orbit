package com.example.demo.service;

import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;
import org.springframework.transaction.event.TransactionPhase;
import org.springframework.transaction.event.TransactionalEventListener;

@Component
@RequiredArgsConstructor
public class StageChangedEventListener {

    private final StageCommandService stageCommandService;

    @TransactionalEventListener(
            phase = TransactionPhase.AFTER_COMMIT
    )
    public void onStageChanged(StageChangedEvent event) {
        stageCommandService.sendStage(
                event.userId(),
                event.stage()
        );
    }
}