package com.example.demo.service;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import javax.crypto.Cipher;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.security.SecureRandom;
import java.util.Base64;

@Service
public class CryptoService {

    private static final String ALGORITHM = "AES/GCM/NoPadding";

    // AES-GCM에서 일반적으로 사용하는 12byte IV
    private static final int IV_LENGTH = 12;

    // 인증 태그 길이
    private static final int TAG_LENGTH = 128;

    private final SecretKey secretKey;

    private final SecureRandom secureRandom = new SecureRandom();

    public CryptoService(
            @Value("${app.crypto.key}") String base64Key) {

        byte[] decodedKey =
                Base64.getDecoder().decode(base64Key);

        this.secretKey =
                new SecretKeySpec(decodedKey, "AES");
    }

    public String encrypt(String plainText) {

        try {

            byte[] iv = new byte[IV_LENGTH];
            secureRandom.nextBytes(iv);

            Cipher cipher =
                    Cipher.getInstance(ALGORITHM);

            GCMParameterSpec parameterSpec =
                    new GCMParameterSpec(TAG_LENGTH, iv);

            cipher.init(
                    Cipher.ENCRYPT_MODE,
                    secretKey,
                    parameterSpec
            );

            byte[] encrypted =
                    cipher.doFinal(
                            plainText.getBytes(
                                    StandardCharsets.UTF_8
                            )
                    );

            String encodedIv =
                    Base64.getEncoder()
                            .encodeToString(iv);

            String encodedMessage =
                    Base64.getEncoder()
                            .encodeToString(encrypted);

            return encodedIv + ":" + encodedMessage;

        } catch (Exception e) {

            throw new RuntimeException(
                    "대화 내용 암호화 실패",
                    e
            );
        }
    }

    public String decrypt(String encryptedText) {

        try {

            String[] parts =
                    encryptedText.split(":", 2);

            byte[] iv =
                    Base64.getDecoder()
                            .decode(parts[0]);

            byte[] encrypted =
                    Base64.getDecoder()
                            .decode(parts[1]);

            Cipher cipher =
                    Cipher.getInstance(ALGORITHM);

            GCMParameterSpec parameterSpec =
                    new GCMParameterSpec(TAG_LENGTH, iv);

            cipher.init(
                    Cipher.DECRYPT_MODE,
                    secretKey,
                    parameterSpec
            );

            byte[] decrypted =
                    cipher.doFinal(encrypted);

            return new String(
                    decrypted,
                    StandardCharsets.UTF_8
            );

        } catch (Exception e) {

            throw new RuntimeException(
                    "대화 내용 복호화 실패",
                    e
            );
        }
    }
}