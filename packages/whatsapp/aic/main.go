package main

import (
	"fmt"
	"github.com/TheZoraiz/ascii-image-converter/aic_package"
	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/credentials"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/s3"
	"io"
	"os"
	"reflect"
)

func Handle(err error) map[string]interface{} {
	msg := make(map[string]interface{})
	fmt.Println("Error: ", err)
	msg["body"] = fmt.Sprintln("Error: ", err)
	return msg
}

func ParseArgs(args map[string]interface{}) (string, aic_package.Flags, error) {
	fileKey, ok := args["media_id"].(string)
	flags := aic_package.DefaultFlags()
	if !ok {
		return "", flags, fmt.Errorf("no media_id provided")
	}
	widthFlt64, ok := args["width"].(float64)
	if !ok {
		Handle(fmt.Errorf("no width provided"))
	}
	width := int(widthFlt64) * 2 // Multiply by 2 to maintain aspect ratio
	heightFlt64, ok := args["height"].(float64)
	if !ok {
		Handle(fmt.Errorf("no height provided"))
	}
	height := int(heightFlt64)
	flags.Dimensions = []int{width, height}
	flags.Complex, ok = args["complex"].(bool)
	if !ok {
		Handle(fmt.Errorf("no use complex chars flag provided"))
	}
	flags.Negative, ok = args["negative"].(bool)
	if !ok {
		Handle(fmt.Errorf("no negative flag provided"))
	}
	flags.FlipX, ok = args["flip_x"].(bool)
	if !ok {
		Handle(fmt.Errorf("no flip_x flag provided"))
	}
	flags.FlipY, ok = args["flip_y"].(bool)
	if !ok {
		Handle(fmt.Errorf("no flip_y flag provided"))
	}
	return fileKey, flags, nil
}

func Main(args map[string]interface{}) map[string]interface{} {
	outputImageSuffix := "-ascii-art.png"
	for key, value := range args {
		fmt.Println("Key:", key, "Value:", value, "Type:", reflect.TypeOf(value))
	}
	fileKey, flags, err := ParseArgs(args)
	if err != nil {
		return Handle(err)
	}
	fmt.Println("Processing image with media_id:", fileKey)
	key := os.Getenv("SPACES_KEY")
	secret := os.Getenv("SPACES_SECRET")

	s3Config := &aws.Config{
		Credentials:      credentials.NewStaticCredentials(key, secret, ""),
		Endpoint:         aws.String("https://nyc3.digitaloceanspaces.com"),
		Region:           aws.String("us-east-1"),
		S3ForcePathStyle: aws.Bool(false),
	}
	newSession, err := session.NewSession(s3Config)
	if err != nil {
		return Handle(err)
	}
	s3Client := s3.New(newSession)
	image, err := s3Client.GetObject(&s3.GetObjectInput{
		Bucket: aws.String(os.Getenv("SPACES_NAME")),
		Key:    aws.String(fileKey + ".jpeg"),
	})
	if err != nil {
		return Handle(err)
	}
	file, err := os.Create("/tmp/" + fileKey + ".jpeg")
	if err != nil {
		return Handle(err)
	}
	_, err = io.Copy(file, image.Body)
	if err != nil {
		return Handle(err)
	}
	defer file.Close()
	defer image.Body.Close()

	flags.SaveImagePath = "/tmp/"
	flags.OnlySave = true
	fmt.Println("Converting image:", fileKey+".jpeg")
	_, err = aic_package.Convert("/tmp/"+fileKey+".jpeg", flags)
	if err != nil {
		return Handle(err)
	}
	fmt.Println("Converted image:", fileKey+".jpeg", "to:", "/tmp/"+fileKey+outputImageSuffix)
	file, err = os.Open("/tmp/" + fileKey + outputImageSuffix)
	if err != nil {
		return Handle(err)
	}

	_, err = s3Client.PutObject(&s3.PutObjectInput{
		Bucket: aws.String(os.Getenv("SPACES_NAME")),
		Key:    aws.String(fileKey + outputImageSuffix),
		Body:   file,
	})
	defer file.Close()
	if err != nil {
		return Handle(err)
	}
	msg := make(map[string]interface{})
	msg["body"] = fileKey + outputImageSuffix
	return msg
}
