package com.example.demo.service;

import com.example.demo.domain.CharacterRepository;
import com.example.demo.domain.CharacterStatus;
import com.example.demo.dto.DeviceRequest;
import com.example.demo.dto.DeviceResponse;
import com.example.demo.entity.Device;
import com.example.demo.repository.DeviceRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

@Service
@RequiredArgsConstructor
public class DeviceService {

    private final DeviceRepository deviceRepository;
    private final CharacterRepository characterRepository;

    // 기기 등록
    @Transactional
    public DeviceResponse registerDevice(DeviceRequest request) {

        // 1. 필수값 확인
        if (request.getDeviceId() == null ||
                request.getDeviceId().isBlank() ||
                request.getCharId() == null ||
                request.getUserId() == null) {

            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "deviceId, charId, userId는 필수입니다."
            );
        }

        // 2. 이미 등록된 deviceId인지 확인
        if (deviceRepository.existsByDeviceId(request.getDeviceId())) {
            throw new ResponseStatusException(
                    HttpStatus.CONFLICT,
                    "이미 등록된 기기입니다."
            );
        }

        // 3. 이미 다른 기기에 연결된 캐릭터인지 확인
        if (deviceRepository.existsByCharId(request.getCharId())) {
            throw new ResponseStatusException(
                    HttpStatus.CONFLICT,
                    "이미 다른 기기에 연결된 캐릭터입니다."
            );
        }

        // 4. 이미 다른 기기에 연결된 사용자인지 확인
        if (deviceRepository.existsByUserId(request.getUserId())) {
            throw new ResponseStatusException(
                    HttpStatus.CONFLICT,
                    "이미 다른 기기에 연결된 사용자입니다."
            );
        }

        // 5. 실제 캐릭터 존재 여부 확인
        CharacterStatus character = characterRepository
                .findById(request.getCharId())
                .orElseThrow(() ->
                        new ResponseStatusException(
                                HttpStatus.NOT_FOUND,
                                "캐릭터를 찾을 수 없습니다."
                        )
                );

        // 6. 요청 userId와 캐릭터 userId가 같은지 확인
        if (!request.getUserId().equals(character.getUserId())) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "해당 사용자의 캐릭터가 아닙니다."
            );
        }

        // 7. Device 저장
        Device device = new Device(
                request.getDeviceId(),
                request.getCharId(),
                request.getUserId()
        );

        Device saved = deviceRepository.save(device);

        return DeviceResponse.from(saved);
    }

    // deviceId로 기기 조회
    @Transactional(readOnly = true)
    public DeviceResponse getDevice(String deviceId) {

        Device device = deviceRepository
                .findByDeviceId(deviceId)
                .orElseThrow(() ->
                        new ResponseStatusException(
                                HttpStatus.NOT_FOUND,
                                "등록된 기기를 찾을 수 없습니다."
                        )
                );

        return DeviceResponse.from(device);
    }

    // deviceId로 charId 조회
    @Transactional(readOnly = true)
    public Long getCharIdByDeviceId(String deviceId) {

        Device device = deviceRepository
                .findByDeviceId(deviceId)
                .orElseThrow(() ->
                        new ResponseStatusException(
                                HttpStatus.NOT_FOUND,
                                "등록된 기기를 찾을 수 없습니다."
                        )
                );

        return device.getCharId();
    }
}