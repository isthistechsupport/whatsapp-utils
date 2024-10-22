package main


import (
	"fmt"
	"io"
	"os"
	//"reflect"
	"github.com/TheZoraiz/ascii-image-converter/aic_package"
	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/credentials"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/s3"
)


func Main(args map[string]interface{}) map[string]interface{} {
	msg := make(map[string]interface{})
	//for key, value := range args {
	//	fmt.Printf("Key: %s, Value: %v (Type: %s)\n", key, value, reflect.TypeOf(value))
	//}
	outputImageSuffix := "-ascii-art.png"
	file_key, ok := args["media_id"].(string)
	if !ok {
		fmt.Println("Error getting media_id")
		msg["body"] = fmt.Sprintln("Error getting media_id")
		return msg
	}
	fmt.Println("Processing image with media_id:", file_key)
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
		fmt.Println("Error creating session: ", err)
		msg["body"] = fmt.Sprintln("Error creating session: ", err)
		return msg
	}
	s3Client := s3.New(newSession)
	image, err := s3Client.GetObject(&s3.GetObjectInput{
		Bucket: aws.String(os.Getenv("SPACES_NAME")),
		Key:    aws.String(file_key + ".jpeg"),
	})
	if err != nil {
		fmt.Println("Error getting object: ", err)
		msg["body"] = fmt.Sprintln("Error getting object: ", err)
		return msg
	}
	file, err := os.Create("/tmp/" + file_key + ".jpeg")
	if err != nil {
		fmt.Println("Error creating file: ", err)
		msg["body"] = fmt.Sprintln("Error creating file: ", err)
		return msg
	}
	_, err = io.Copy(file, image.Body)
	if err != nil {
		fmt.Println("Error saving file: ", err)
		msg["body"] = fmt.Sprintln("Error saving file: ", err)
		return msg
	}
	defer file.Close()
	defer image.Body.Close()

	flags := aic_package.DefaultFlags()
	widthFlt64, wok := args["width"].(float64)
	if !wok {
		fmt.Println("No width provided")
	}
	width := int(widthFlt64) * 2 // Multiply by 2 to maintain aspect ratio
	fmt.Println("Width:", width)
	heightFlt64, hok := args["height"].(float64)
	if !hok {
		fmt.Println("No height provided")
	}
	height := int(heightFlt64)
	fmt.Println("Height:", height)
	if wok && hok {
		flags.Dimensions = []int{width, height}
	} else if wok {
		flags.Width = width
	} else if hok {
		flags.Height = height
	}
	flags.SaveImagePath = "/tmp/"
	fmt.Println("Converting image:", file_key+".jpeg")
	_, err = aic_package.Convert("/tmp/"+file_key+".jpeg", flags)
	if err != nil {
		fmt.Println("Error converting image: ", err)
		msg["body"] = fmt.Sprintln("Error converting image: ", err)
		return msg
	}
	fmt.Println("Converted image:", file_key+".jpeg", "to:", "/tmp/"+file_key+outputImageSuffix)
	file, err = os.Open("/tmp/" + file_key + outputImageSuffix)
	if err != nil {
		fmt.Println("Error opening file: ", err)
		msg["body"] = fmt.Sprintln("Error opening file: ", err)
		return msg
	}

	_, err = s3Client.PutObject(&s3.PutObjectInput{
		Bucket: aws.String(os.Getenv("SPACES_NAME")),
		Key:    aws.String(file_key + outputImageSuffix),
		Body:   file,
	})
	defer file.Close()
	if err != nil {
		fmt.Println("Error uploading file: ", err)
		msg["body"] = fmt.Sprintln("Error uploading file: ", err)
		return msg
	}
	msg["body"] = file_key + outputImageSuffix
	return msg
}
